from pathlib import Path
from subprocess import TimeoutExpired
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from zipfile import ZipFile

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject

from ttree.cli import inspect, render
from ttree.documents import WORD_NS, _run_doc_reader, extract_doc, extract_docx, extract_pdf
from test_cli import FakeTokenizer


def make_docx(path, body, extras=None):
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{WORD_NS[1:-1]}"><w:body>{body}</w:body></w:document>')
        for name, xml in (extras or {}).items():
            archive.writestr(name, xml)


def make_pdf(path, text=None, *, image=False, encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    if text is not None:
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 200 Td (" + text.encode("ascii") + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if image:
        picture = DecodedStreamObject()
        picture.set_data(b"\xff\x00\x00")
        picture.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                        NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                        NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im1"): writer._add_object(picture)})})
        stream = DecodedStreamObject()
        stream.set_data(b"q 100 0 0 100 20 20 cm /Im1 Do Q")
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("synthetic-test-password")
    writer.write(path)


class DocumentTests(TestCase):
    def test_docx_headings_runs_lists_tables_headers_and_notes(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "sample.DOCX"
            make_docx(path,
                '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Heading</w:t></w:r></w:p>'
                '<w:p><w:r><w:t>First </w:t></w:r><w:r><w:t>paragraph</w:t><w:tab/><w:t>end</w:t><w:br/><w:t>line</w:t></w:r></w:p>'
                '<w:p><w:pPr><w:numPr><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>Item</w:t></w:r></w:p>'
                '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell A</w:t></w:r></w:p></w:tc>'
                '<w:tc><w:p><w:r><w:t>Cell B</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
                '<w:p><w:del><w:r><w:delText>Deleted</w:delText></w:r></w:del><w:r><w:instrText>FIELD</w:instrText></w:r></w:p>',
                {"word/header1.xml": f'<w:hdr xmlns:w="{WORD_NS[1:-1]}"><w:p><w:r><w:t>Header</w:t></w:r></w:p></w:hdr>',
                 "word/footnotes.xml": f'<w:footnotes xmlns:w="{WORD_NS[1:-1]}"><w:footnote w:id="1"><w:p><w:r><w:t>Note</w:t></w:r></w:p></w:footnote></w:footnotes>'})
            result = extract_docx(path)
            self.assertIsNone(result.issue)
            self.assertIn("# Heading\nFirst paragraph\tend\nline\n- Item\nCell A\tCell B", result.text)
            self.assertIn("Header", result.text)
            self.assertIn("Note", result.text)
            self.assertNotIn("Deleted", result.text)
            self.assertNotIn("FIELD", result.text)
            entry = inspect(path, FakeTokenizer(), False)
            self.assertEqual(entry.tokens, len(result.text.encode("utf-8")))
            self.assertEqual(entry.size, path.stat().st_size)

    def test_image_only_documents_do_not_claim_tokens(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_docx(root / "image.docx", '<w:p><w:r><w:drawing/></w:r></w:p>')
            make_pdf(root / "image.pdf", image=True)
            entry = inspect(root, FakeTokenizer(), False)
            self.assertEqual((entry.tokens, entry.counted, entry.incomplete), (0, 0, False))
            lines = render(entry, exact=True, depth=None, sort=False)
            self.assertEqual(sum("[no text]" in line for line in lines), 2)
            self.assertTrue(all("tok" not in line for line in lines))

    def test_strict_docx_namespace_and_invalid_document_xml(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "strict.docx"
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", '<w:document xmlns:w="http://purl.oclc.org/ooxml/wordprocessingml/main"><w:body><w:p><w:r><w:t>Strict text</w:t></w:r></w:p></w:body></w:document>')
            self.assertEqual(extract_docx(path).text, "Strict text")
            with ZipFile(path, "w") as archive:
                archive.writestr("word/document.xml", '<unrelated/>')
            self.assertIn("invalid", extract_docx(path).issue)

    def test_pdf_existing_text_and_encryption(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            make_pdf(root / "text.PDF", "Readable document text")
            make_pdf(root / "locked.pdf", "Private", encrypted=True)
            self.assertEqual(extract_pdf(root / "text.PDF").text, "Readable document text")
            entry = inspect(root, FakeTokenizer(), False)
            self.assertGreater(entry.tokens, 0)
            self.assertTrue(entry.incomplete)
            lines = render(entry, exact=True, depth=None, sort=False)
            self.assertIn("≥", lines[0])
            self.assertTrue(any("encrypted PDF" in line and "tok" not in line for line in lines))

    def test_malformed_documents_and_docx_size_limit(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for suffix in (".pdf", ".docx"):
                path = root / ("bad" + suffix)
                path.write_bytes(b"Malformed private text")
                entry = inspect(path, FakeTokenizer(), False)
                self.assertTrue(entry.incomplete)
                self.assertEqual(entry.counted, 0)
                self.assertNotIn("private", entry.issue)
            path = root / "large.docx"
            make_docx(path, '<w:p><w:r><w:t>Large</w:t></w:r></w:p>')
            with patch("ttree.documents.MAX_DOCX_XML_BYTES", 1):
                self.assertIn("limit", extract_docx(path).issue)

    def test_partial_pdf_preserves_lower_bound_without_leaking_errors(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "partial.pdf"
            path.write_bytes(b"placeholder")
            good = type("Page", (), {"extract_text": lambda _: "Readable"})()
            broken = type("Page", (), {"extract_text": lambda _: (_ for _ in ()).throw(ValueError("private text"))})()
            reader = type("Reader", (), {"is_encrypted": False, "pages": [good, broken]})()
            with patch("pypdf.PdfReader", return_value=reader):
                entry = inspect(path, FakeTokenizer(), False)
            self.assertEqual(entry.tokens, 8)
            self.assertTrue(entry.incomplete)
            self.assertNotIn("private", render(entry, exact=True, depth=None, sort=False)[0])

    def test_doc_reader_missing_timeout_and_conversion_failure(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "sample.doc"
            path.write_bytes(b"fake legacy document")
            with patch("ttree.documents.shutil.which", return_value=None):
                self.assertIn("reader unavailable", extract_doc(path).issue)
                entry = inspect(path, FakeTokenizer(), False)
                self.assertTrue(entry.incomplete)
                self.assertEqual(entry.counted, 0)
            with patch("ttree.documents.shutil.which", return_value="libreoffice"):
                with patch("ttree.documents._run_doc_reader", side_effect=TimeoutExpired("reader", 60)):
                    self.assertIn("timed out", extract_doc(path).issue)
                with patch("ttree.documents._run_doc_reader", return_value=0):
                    self.assertIn("cannot extract", extract_doc(path).issue)

    def test_doc_conversion_is_private_and_preserves_original(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "sample.doc"
            path.write_bytes(b"original")
            def convert(command):
                work = Path(command[-1]).parent
                self.assertEqual((work / "input.doc").read_bytes(), b"original")
                config = (work / "profile/user/registrymodifications.xcu").read_text()
                self.assertIn('oor:name="Link" oor:op="fuse"><value>2</value>', config)
                self.assertIn('oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value>', config)
                self.assertIn('oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value>', config)
                (work / "input.txt").write_text("\ufeffOlá DOC", encoding="utf-8")
                return 0
            with patch("ttree.documents.shutil.which", return_value="libreoffice"), patch("ttree.documents._run_doc_reader", side_effect=convert):
                self.assertEqual(extract_doc(path).text, "Olá DOC")
            self.assertEqual(path.read_bytes(), b"original")
            self.assertEqual(list(Path(temp).iterdir()), [path])

    def test_doc_timeout_terminates_private_process_group(self):
        with patch("ttree.documents.subprocess.Popen") as start, patch("ttree.documents.os.killpg") as kill:
            process = start.return_value.__enter__.return_value
            process.wait.side_effect = [TimeoutExpired("reader", 60), 0]
            with self.assertRaises(TimeoutExpired):
                _run_doc_reader(["reader"])
            if start.call_args.kwargs["start_new_session"]:
                kill.assert_called_once()
            else:
                process.kill.assert_called_once()
            self.assertEqual(process.wait.call_count, 2)
