"""Public CLI/agent contract regressions using real bounded workers."""

import base64
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from ttree.cli import (
    compact,
    ensure_tokenizer_file,
    load_tokenizer,
    main,
    tokenizer_path,
)
from ttree.limits import validated
from ttree.scan import scan_roots


class TreeTests(TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "ttree.cli", *map(str, args)],
            capture_output=True,
            text=True,
            timeout=25,
            env={**os.environ, "TMPDIR": str(self.root)},
        )

    def result(self, *args):
        result = self.cli("--json", *args)
        value = json.loads(result.stdout)
        self.assertTrue(result.stdout.endswith("\n"))
        self.assertEqual(result.stderr, "")
        self.assertEqual(value["schema_version"], 1)
        return result.returncode, value

    def test_compact_pt_br_units(self):
        self.assertEqual(compact(68027, ("B", "kB", "MB"), False), "68 kB")
        self.assertEqual(compact(1234567, ("B", "kB", "MB"), True), "1.234.567 B")

    def test_bundled_vocabulary_without_network(self):
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            ensure_tokenizer_file(tokenizer_path())
            self.assertEqual(len(load_tokenizer().encode(b"Hello, world!")), 4)

    def test_vocabulary_rejects_bad_hash(self):
        path = self.root / "bad"
        path.write_bytes(b"bad")
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            ensure_tokenizer_file(path)

    def test_json_totals_all_entries_and_display_flags(self):
        (self.root / "sub").mkdir()
        (self.root / "sub/a.md").write_text("Hello, world!")
        (self.root / "b.md").write_text("Readable ordinary text")
        code, value = self.result(self.root)
        self.assertEqual(code, 0)
        self.assertEqual(value["total"]["tokens"], 7)
        self.assertEqual(value["roots"][0]["tokens"], 7)
        self.assertTrue(value["total"]["complete"])
        for flags in [("-h", "--exact"), ("-L", "1"), ("--sort",)]:
            _, other = self.result(*flags, self.root)
            self.assertEqual(value, other)
        self.assertEqual(
            {entry["path"] for entry in value["roots"][0]["entries"]},
            {".", "sub", "sub/a.md", "b.md"},
        )

    def test_doc_quarantine_null_and_strict_precedence(self):
        legacy = self.root / "private.doc"
        legacy.write_bytes(bytes.fromhex("d0cf11e0a1b11ae1") + b"private")
        code, value = self.result("--strict", legacy)
        root = value["roots"][0]
        self.assertEqual(code, 3)
        self.assertEqual(
            (root["status"], root["tokens"], root["complete"], root["bytes"]),
            ("unsupported", None, False, 15),
        )
        code, value = self.result("--strict", legacy, self.root / "missing")
        self.assertEqual(code, 1)
        self.assertEqual(value["roots"][1]["status"], "missing")
        self.assertIsNone(value["roots"][1]["tokens"])
        self.assertIsNone(value["roots"][1]["bytes"])
        self.assertEqual(self.result(legacy)[0], 0)

    def test_bom_empty_non_utf8_and_binary_policy(self):
        for encoding in ("utf-16", "utf-32", "utf-8-sig"):
            (self.root / (encoding + ".txt")).write_bytes(
                "Hello, world!".encode(encoding)
            )
        (self.root / "empty.txt").touch()
        (self.root / "bad.txt").write_bytes(b"\xffprivate")
        (self.root / "bad.dat").write_bytes(b"\0private")
        (self.root / "image.png").write_bytes(b"\x89PNG\0")
        (self.root / "sheet.xlsx").write_bytes(b"private")
        code, value = self.result("--strict", self.root)
        self.assertEqual(code, 3)
        entries = {entry["path"]: entry for entry in value["roots"][0]["entries"]}
        for encoding in ("utf-16", "utf-32", "utf-8-sig"):
            self.assertEqual(entries[encoding + ".txt"]["tokens"], 4)
        self.assertEqual(
            (entries["empty.txt"]["tokens"], entries["empty.txt"]["status"]),
            (0, "empty"),
        )
        for name in ("bad.txt", "bad.dat"):
            self.assertEqual(entries[name]["status"], "not_utf8")
            self.assertIsNone(entries[name]["tokens"])
        self.assertTrue(entries["image.png"]["complete"])
        self.assertEqual(entries["sheet.xlsx"]["status"], "unsupported")

    def test_symlinks_explicit_descendant_and_ancestor(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "s.txt").write_text("SENTINEL " * 1000)
        scanned = self.root / "scanned"
        scanned.mkdir()
        (scanned / "link").symlink_to(outside, target_is_directory=True)
        code, value = self.result("--strict", scanned)
        self.assertEqual(code, 0)
        self.assertEqual(value["total"]["tokens"], 0)
        code, value = self.result("--strict", scanned / "link")
        self.assertEqual(code, 3)
        self.assertEqual(value["roots"][0]["status"], "link_not_followed")
        code, value = self.result("--strict", str(scanned / "link") + "/s.txt")
        self.assertEqual(code, 3)
        self.assertIsNone(value["total"]["tokens"])
        code, value = self.result(
            "--strict", str(scanned / "link") + "/../outside/s.txt"
        )
        self.assertEqual(code, 3)

    def test_human_control_escape_and_posix_raw_path_roundtrip(self):
        raw = os.fsencode(self.root) + b"/unsafe\n\x1b\xff\xe2\x80\xae.txt"
        fd = os.open(raw, os.O_CREAT | os.O_WRONLY, 0o600)
        os.write(fd, b"x")
        os.close(fd)
        code, value = self.result(self.root)
        entry = next(
            entry for entry in value["roots"][0]["entries"] if entry["kind"] == "file"
        )
        self.assertEqual(
            base64.b64decode(entry["path_bytes_base64"]), raw.rsplit(b"/", 1)[1]
        )
        shown = self.cli(self.root).stdout
        self.assertIn(r"\u000a", shown)
        self.assertIn(r"\u001b", shown)
        self.assertIn(r"\udcff", shown)
        self.assertIn(r"\u202e", shown)
        self.assertNotIn("\x1b", shown)

    def test_limits_usage_and_actual_input_cap(self):
        path = self.root / "a.txt"
        path.write_text("Hello")
        for value in ("0", "-1", "67108865"):
            self.assertEqual(self.cli("--limit-input-bytes", value, path).returncode, 2)
        code, result = self.result("--strict", "--limit-input-bytes", "4", path)
        self.assertEqual(code, 3)
        self.assertEqual(result["roots"][0]["status"], "too_large")
        self.assertEqual(result["effective_limits"]["input_bytes"], 4)

    def test_unknown_empty_and_mixed_aggregates(self):
        unreadable = self.root / "unreadable"
        unreadable.mkdir()
        (unreadable / "hidden.txt").write_text("Hello, world!")
        empty = self.root / "empty"
        empty.mkdir()
        failed = self.root / "failed.txt"
        failed.write_bytes(b"\xffabc")
        excluded = self.root / "image.png"
        excluded.write_bytes(b"PNG")
        normal = self.root / "normal.txt"
        normal.write_text("Hello, world!")
        unreadable.chmod(0)
        try:
            code, value = self.result("--strict", unreadable)
            self.assertEqual(code, 3)
            self.assertEqual(value["roots"][0]["status"], "unreadable")
            self.assertEqual(
                value["total"], {"tokens": None, "bytes": None, "complete": False}
            )
            _, value = self.result("--strict", self.root)
            entries = {e["path"]: e for e in value["roots"][0]["entries"]}
            self.assertIsNone(entries["unreadable"]["tokens"])
            self.assertIsNone(entries["unreadable"]["bytes"])
            self.assertEqual(
                (entries["empty"]["tokens"], entries["empty"]["bytes"]), (0, 0)
            )
            self.assertEqual(
                (entries["failed.txt"]["tokens"], entries["failed.txt"]["bytes"]),
                (None, 4),
            )
            self.assertEqual(entries["image.png"]["tokens"], 0)
            self.assertEqual(
                value["total"], {"tokens": 4, "bytes": 20, "complete": False}
            )
            _, mixed = self.result("--strict", unreadable, failed)
            self.assertEqual(
                mixed["total"], {"tokens": None, "bytes": 4, "complete": False}
            )
            _, zero = self.result("--strict", unreadable, empty, excluded)
            self.assertEqual(
                zero["total"], {"tokens": 0, "bytes": 3, "complete": False}
            )
            shown = self.cli("--strict", unreadable, failed).stdout
            self.assertNotIn("0 tok", shown)
        finally:
            unreadable.chmod(0o700)

    def test_human_literal_escape_line_separators_roots_and_links(self):
        names = ["literal\\u2028.txt", "actual\u2028.txt", "paragraph\u2029.txt"]
        for name in names:
            (self.root / name).touch()
        (self.root / "target-link").symlink_to("target\\u2028\u2028\u2029\n")
        shown = self.cli(self.root).stdout
        self.assertEqual(len(shown.splitlines()), 5)
        self.assertIn(r"literal\\u2028.txt", shown)
        self.assertIn(r"actual\u2028.txt", shown)
        self.assertIn(r"target\\u2028\u2028\u2029\u000a", shown)
        root = self.cli(self.root / names[1]).stdout
        self.assertEqual(len(root.splitlines()), 1)
        self.assertIn(r"actual\u2028.txt", root)
        _, value = self.result(self.root)
        self.assertEqual(
            {e["path"] for e in value["roots"][0]["entries"]},
            {".", "target-link", *names},
        )

    def test_unenumerated_timed_out_directory_and_unknown_only_parent(self):
        (self.root / "pending").mkdir()
        real_scandir = os.scandir
        expired = False

        @contextlib.contextmanager
        def enumerate_then_expire(fd):
            nonlocal expired
            with real_scandir(fd) as iterator:
                yield iterator
            expired = True

        with (
            patch("ttree.scan.os.scandir", enumerate_then_expire),
            patch("ttree.scan.time.monotonic", side_effect=lambda: 2 if expired else 0),
        ):
            roots = scan_roots([str(self.root)], validated(), 1)
        self.assertEqual(roots[0][1][1].status, "timed_out")
        for entry in roots[0][1]:
            self.assertIsNone(entry.tokens)
            self.assertIsNone(entry.bytes)
            self.assertFalse(entry.complete)
        for flags in (("--json", "--strict"), ("--strict",)):
            output = io.StringIO()
            with (
                patch("ttree.cli.scan_roots", return_value=roots),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(main([*flags, str(self.root)]), 3)
            if "--json" in flags:
                value = json.loads(output.getvalue())
                self.assertIsNone(value["total"]["tokens"])
                self.assertIsNone(value["roots"][0]["bytes"])
            else:
                self.assertNotIn("0 tok", output.getvalue())
        (self.root / "pending/failed.txt").write_bytes(b"\xffabc")
        _, value = self.result("--strict", self.root)
        self.assertIsNone(value["total"]["tokens"])
        self.assertEqual(value["total"]["bytes"], 4)

    def test_budget_marks_incomplete_and_keeps_next_root(self):
        scanned = self.root / "scanned"
        scanned.mkdir()
        for index in range(4):
            (scanned / str(index)).write_text("x")
        next_root = self.root / "next"
        next_root.write_text("Hello, world!")
        code, value = self.result(
            "--strict", "--limit-entries", "3", scanned, next_root
        )
        self.assertEqual(code, 3)
        self.assertFalse(value["roots"][0]["complete"])
        self.assertEqual(value["roots"][1]["tokens"], 4)
        self.assertLessEqual(sum(len(root["entries"]) for root in value["roots"]), 3)
