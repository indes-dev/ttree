"""Real document workers: normal, malformed, damaged and encrypted files."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from zipfile import ZipFile

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(path, body, extras=None):
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{WORD}"><w:body>{body}</w:body></w:document>',
        )
        for name, xml in (extras or {}).items():
            archive.writestr(name, xml)


def make_pdf(path, text=None, *, password=None):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    if text:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                )
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 200 Td (" + text.encode("ascii") + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if password is not None:
        writer.encrypt(password)
    writer.write(path)


class DocumentTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def scan(self, *paths):
        result = subprocess.run(
            [sys.executable, "-m", "ttree.cli", "--json", "--strict", *map(str, paths)],
            capture_output=True,
            text=True,
            timeout=25,
            env={**os.environ, "TMPDIR": str(self.root)},
        )
        self.assertNotIn("private", result.stdout)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)["roots"]

    def test_normal_docx_pdf_empty_and_encrypted_empty_password(self):
        docx = self.root / "normal.DOCX"
        make_docx(docx, "<w:p><w:r><w:t>Readable DOCX text</w:t></w:r></w:p>")
        pdf = self.root / "normal.PDF"
        make_pdf(pdf, "Readable PDF text")
        empty = self.root / "image.pdf"
        make_pdf(empty)
        locked = self.root / "locked.pdf"
        make_pdf(locked, "Secret", password="secret")
        unlocked = self.root / "empty-password.pdf"
        make_pdf(unlocked, "Readable PDF text", password="")
        code, roots = self.scan(docx, pdf, empty, locked, unlocked)
        self.assertEqual(code, 3)
        self.assertEqual([root["tokens"] for root in roots], [4, 3, 0, None, 3])
        self.assertEqual(
            [root["status"] for root in roots],
            ["counted", "counted", "no_text", "encrypted", "counted"],
        )

    def test_malformed_documents_continue(self):
        bad = self.root / "bad.docx"
        bad.write_bytes(b"private invalid ZIP")
        other = self.root / "bad.pdf"
        other.write_bytes(b"private invalid PDF")
        text = self.root / "ok.txt"
        text.write_text("Hello, world!")
        code, roots = self.scan(bad, other, text)
        self.assertEqual(code, 3)
        self.assertEqual(roots[0]["status"], "failed")
        self.assertIn(roots[1]["status"], ("failed", "partial"))
        self.assertEqual(roots[2]["tokens"], 4)

    def test_xml_declarations_rejected_across_encodings(self):
        for encoding in ("utf-8", "utf-16", "utf-32"):
            path = self.root / (encoding + ".docx")
            xml = (
                '<?xml version="1.0"?><!DOCTYPE doc [<!ENTITY x "private">]><w:document xmlns:w="'
                + WORD
                + '"><w:body><w:p><w:r><w:t>&x;</w:t></w:r></w:p></w:body></w:document>'
            ).encode(encoding)
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            code, roots = self.scan(path)
            self.assertEqual(code, 3)
            self.assertEqual(roots[0]["status"], "failed")
            self.assertIsNone(roots[0]["tokens"])

    def test_duplicate_members_rejected(self):
        path = self.root / "duplicate.docx"
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", "<x/>")
                archive.writestr("word/document.xml", "<x/>")
        code, roots = self.scan(path)
        self.assertEqual(code, 3)
        self.assertEqual(roots[0]["status"], "failed")
