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

    def test_benign_padded_snapshot_sizes_and_independent_response_limit(self):
        # Stored unused padding, not compressed expansion or active content.
        from zipfile import ZIP_STORED

        mib = 1024 * 1024
        body = f'<w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:t>Readable DOCX text</w:t></w:r></w:p></w:body></w:document>'
        paths = []
        for size in (11 * mib, 13 * mib, 64 * mib, 64 * mib + 1):
            path = self.root / f"padded-{size}.docx"
            with ZipFile(path, "w", compression=ZIP_STORED) as archive:
                archive.writestr("word/document.xml", body)
                archive.writestr("padding.bin", b"")
            padding = size - path.stat().st_size
            with ZipFile(path, "w", compression=ZIP_STORED) as archive:
                archive.writestr("word/document.xml", body)
                with archive.open("padding.bin", "w") as output:
                    while padding:
                        chunk = min(padding, mib)
                        output.write(b"x" * chunk)
                        padding -= chunk
            self.assertEqual(path.stat().st_size, size)
            paths.append(path)
        normal = self.root / "following.txt"
        normal.write_text("Hello, world!")
        code, roots = self.scan(*paths, normal)
        self.assertEqual(code, 3)
        self.assertEqual([r["tokens"] for r in roots], [4, 4, 4, None, 4])
        self.assertEqual(roots[3]["status"], "too_large")
        for options, expected in [
            (("--limit-response-bytes", "512"), 4),
            (("--limit-input-bytes", str(12 * mib)), None),
        ]:
            code, roots = self.scan(*options, paths[1], normal)
            self.assertEqual(roots[0]["tokens"], expected)
            self.assertEqual(roots[1]["tokens"], 4)

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

    def extracted(self, path):
        from ttree.documents import docx

        with path.open("rb") as source:
            return docx(source, {})[0]

    def test_docx_representation_headers_notes_and_revisions(self):
        path = self.root / "semantics.docx"
        make_docx(
            path,
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Heading</w:t></w:r></w:p>'
            "<w:p><w:r><w:t>First </w:t></w:r><w:r><w:t>paragraph</w:t><w:tab/><w:t>end</w:t><w:br/><w:t>line</w:t></w:r></w:p>"
            '<w:p><w:pPr><w:numPr><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Item</w:t></w:r></w:p>'
            "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Cell B</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
            "<w:p><w:del><w:r><w:t>Deleted</w:t></w:r></w:del><w:moveFrom><w:r><w:t>Moved away</w:t></w:r></w:moveFrom><w:moveTo><w:r><w:t>Moved here</w:t></w:r></w:moveTo><w:r><w:instrText>FIELD</w:instrText></w:r></w:p>",
            {
                "word/header1.xml": f'<w:hdr xmlns:w="{WORD}"><w:p><w:r><w:t>Header</w:t></w:r></w:p></w:hdr>',
                "word/footnotes.xml": f'<w:footnotes xmlns:w="{WORD}"><w:footnote w:id="0"><w:p><w:r><w:t>Separator</w:t></w:r></w:p></w:footnote><w:footnote w:id="1"><w:p><w:r><w:t>Note</w:t></w:r></w:p></w:footnote></w:footnotes>',
            },
        )
        expected = "# Heading\nFirst paragraph\tend\nline\n- Item\nCell A\tCell B\nMoved here\nNote\nHeader"
        self.assertEqual(self.extracted(path), expected)
        from ttree.cli import load_tokenizer

        code, roots = self.scan(path)
        self.assertEqual(code, 0)
        self.assertEqual(
            roots[0]["tokens"], len(load_tokenizer().encode(expected.encode()))
        )

    def test_alternate_content_selects_one_supported_choice_or_fallback(self):
        mc = "http://schemas.openxmlformats.org/markup-compatibility/2006"
        path = self.root / "alternate.docx"

        def choice(required, text):
            return f'<mc:Choice Requires="{required}"><w:p><w:r><w:t>{text}</w:t></w:r></w:p></mc:Choice>'

        for choices, expected in [
            (choice("w", "Chosen") + choice("w", "Second"), "Chosen"),
            (choice("unknown", "Unavailable"), "Fallback"),
        ]:
            body = (
                f'<mc:AlternateContent xmlns:mc="{mc}" xmlns:unknown="urn:unsupported">'
                + choices
                + "<mc:Fallback><w:p><w:r><w:t>Fallback</w:t></w:r></w:p></mc:Fallback></mc:AlternateContent>"
            )
            make_docx(path, body)
            self.assertEqual(self.extracted(path), expected)
            code, roots = self.scan(path)
            self.assertEqual(code, 0)
            from ttree.cli import load_tokenizer

            self.assertEqual(
                roots[0]["tokens"], len(load_tokenizer().encode(expected.encode()))
            )

    def test_strict_namespace_and_invalid_main_document(self):
        path = self.root / "strict.docx"
        with ZipFile(path, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://purl.oclc.org/ooxml/wordprocessingml/main"><w:body><w:p><w:r><w:t>Strict text</w:t></w:r></w:p></w:body></w:document>',
            )
        self.assertEqual(self.extracted(path), "Strict text")
        self.assertEqual(self.scan(path)[0], 0)
        for xml in ("<unrelated/>", f'<w:document xmlns:w="{WORD}"/>'):
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", xml)
            code, roots = self.scan(path)
            self.assertEqual(code, 3)
            self.assertEqual(roots[0]["status"], "failed")

    def test_recovered_pdf_warnings_remain_partial_without_diagnostics(self):
        path = self.root / "recovered.pdf"
        make_pdf(path, "Readable PDF text")
        raw = path.read_bytes()
        offset = raw.index(b"startxref\n") + len(b"startxref\n")
        end = raw.index(b"\n", offset)
        path.write_bytes(raw[:offset] + b"0" + raw[end:])
        code, roots = self.scan(path)
        self.assertEqual(code, 3)
        self.assertEqual(roots[0]["status"], "partial")
        self.assertEqual(roots[0]["tokens"], 3)

    def test_empty_damaged_pdf_is_partial(self):
        path = self.root / "damaged.pdf"
        make_pdf(path, "x")
        from pypdf import PdfReader

        writer = PdfWriter()
        writer.add_page(PdfReader(path).pages[0])
        page = writer.pages[0]
        stream = DecodedStreamObject()
        stream.set_data(b"private invalid deflate")
        stream[NameObject("/Filter")] = NameObject("/FlateDecode")
        page[NameObject("/Contents")] = writer._add_object(stream)
        writer.write(path)
        code, roots = self.scan(path)
        self.assertEqual(code, 3)
        self.assertEqual(roots[0]["status"], "partial")
        self.assertEqual(roots[0]["tokens"], 0)

    def test_production_actual_docx_expansion_and_structural_caps(self):
        from zipfile import ZIP_DEFLATED

        path = self.root / "expansion.docx"
        with ZipFile(path, "w", ZIP_DEFLATED) as archive:
            archive.writestr(
                "word/document.xml",
                f'<w:document xmlns:w="{WORD}"><w:body>'
                + (" " * 5 * 1024 * 1024)
                + "</w:body></w:document>",
            )
        code, roots = self.scan(path)
        self.assertEqual(code, 3)
        self.assertEqual(roots[0]["status"], "too_large")
        make_docx(path, ("<w:r>" * 130) + ("</w:r>" * 130))
        code, roots = self.scan(path)
        self.assertEqual(code, 3)
        self.assertEqual(roots[0]["status"], "too_large")

    def test_unsupported_pdf_cipher_is_fixed_incomplete(self):
        path = self.root / "unsupported-cipher.pdf"
        make_pdf(path, "Cipher text", password="secret")
        raw = path.read_bytes()
        self.assertIn(b"/V 2", raw)
        path.write_bytes(raw.replace(b"/V 2", b"/V 9"))
        code, roots = self.scan(path)
        self.assertEqual(code, 3)
        self.assertEqual(roots[0]["status"], "failed")
        self.assertIsNone(roots[0]["tokens"])
