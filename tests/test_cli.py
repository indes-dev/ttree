from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ttree.cli import compact, ensure_tokenizer_file, inspect, load_tokenizer, main, render, tokenizer_path


class FakeTokenizer:
    def encode(self, data: bytes) -> list[int]:
        return list(data)


class TreeTests(TestCase):
    def test_subtree_totals_sort_and_display_depth(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            large = root / "large"
            large.mkdir()
            (large / "one.md").write_text("abcdef", encoding="utf-8")
            (root / "small.md").write_text("xy", encoding="utf-8")
            entry = inspect(root, FakeTokenizer(), False)
            lines = render(entry, exact=True, depth=1, sort=True)
            self.assertEqual((entry.size, entry.tokens), (8, 8))
            self.assertIn("8 tok", lines[0])
            self.assertIn("large/ {1 × .md}", lines[1])
            self.assertIn("small.md", lines[2])
            self.assertEqual(len(lines), 3)

    def test_hidden_binary_and_links(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".hidden.md").write_text("secret", encoding="utf-8")
            (root / "binary.dat").write_bytes(b"a\0b")
            (root / "image.png").write_bytes(b"\x89PNG\0\0")
            (root / "loop").symlink_to(root, target_is_directory=True)
            entry = inspect(root, FakeTokenizer(), False)
            self.assertEqual({item.name for item in entry.children}, {"binary.dat", "image.png", "loop"})
            self.assertFalse(entry.incomplete)
            self.assertEqual(entry.tokens, 0)
            lines = render(entry, exact=True, depth=None, sort=False)
            self.assertNotIn("tok", lines[0])
            self.assertTrue(any("binary.dat" in line and "tok" not in line for line in lines))
            self.assertTrue(any("image.png" in line and "tok" not in line for line in lines))

    def test_compact_pt_br_units(self):
        self.assertEqual(compact(68027, ("B", "kB", "MB"), False), "68 kB")
        self.assertEqual(compact(1234567, ("B", "kB", "MB"), False), "1,2 MB")
        self.assertEqual(compact(24922980, ("tok", "ktok", "Mtok"), False), "24,9 Mtok")
        self.assertEqual(compact(1234567, ("B", "kB", "MB"), True), "1.234.567 B")

    def test_bundled_vocabulary_and_first_count_without_network(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            ensure_tokenizer_file(tokenizer_path())
            tokenizer = load_tokenizer()
            self.assertEqual(len(tokenizer.encode(b"Hello, world!")), 4)
            self.assertEqual(len(tokenizer.encode(b"<|endoftext|>")), 7)

    def test_vocabulary_rejects_bad_hash(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "ttree" / "o200k_base.tiktoken"
            path.parent.mkdir()
            path.write_bytes(b"bad")
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                ensure_tokenizer_file(path)
            self.assertEqual(path.read_bytes(), b"bad")
            with self.assertRaisesRegex(RuntimeError, "missing"):
                ensure_tokenizer_file(path.with_name("missing"))

    def test_cli_default_human_exact_and_multiple_roots(self):
        with TemporaryDirectory() as temp:
            first = Path(temp) / "first.md"
            second = Path(temp) / "second.md"
            first.write_text("x" * 1234)
            second.write_text("y" * 5)
            with patch("ttree.cli.load_tokenizer", return_value=FakeTokenizer()):
                for options, expected in [([], "1,2 ktok"), (["--exact"], "1.239 tok"),
                                          (["-h", "--exact"], "1.239 B | 1.239 tok")]:
                    output = StringIO()
                    with redirect_stdout(output):
                        self.assertEqual(main(options + [str(first), str(second)]), 0)
                    result = output.getvalue()
                    self.assertIn("Total:", result)
                    self.assertIn(expected, result)
                    if "-h" not in options:
                        self.assertNotRegex(result, r"\d (?:B|kB|MB)\b")
