import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ttree.cli import compact, ensure_tokenizer_file, inspect, render


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

    def test_vocabulary_download_is_verified_and_cached(self):
        payload = b"verified-vocabulary"
        digest = hashlib.sha256(payload).hexdigest()
        with TemporaryDirectory() as temp:
            path = Path(temp) / "ttree" / "o200k_base.tiktoken"
            with patch("ttree.cli.TOKENIZER_SHA256", digest), patch("ttree.cli.urlopen", return_value=BytesIO(payload)) as download:
                ensure_tokenizer_file(path)
                ensure_tokenizer_file(path)
                self.assertEqual(path.read_bytes(), payload)
                download.assert_called_once()

    def test_vocabulary_rejects_bad_hash(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "ttree" / "o200k_base.tiktoken"
            with patch("ttree.cli.urlopen", return_value=BytesIO(b"bad")):
                with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                    ensure_tokenizer_file(path)
            self.assertFalse(path.exists())
