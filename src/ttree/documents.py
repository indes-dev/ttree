"""Extract document text locally without OCR or document execution."""

from __future__ import annotations

import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

DOCUMENT_SUFFIXES = {".doc", ".docx", ".pdf"}
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
STRICT_WORD_NS = "{http://purl.oclc.org/ooxml/wordprocessingml/main}"
MAX_DOCX_XML_BYTES = 32 * 1024 * 1024
DOC_TIMEOUT_SECONDS = 60


@dataclass
class Extraction:
    text: str = ""
    issue: str | None = None


def _word_text(node: ET.Element) -> str:
    # Deleted revisions, field instructions and image metadata are not text.
    if node.tag == WORD_NS + "del":
        return ""
    if node.tag == WORD_NS + "t":
        return node.text or ""
    if node.tag == WORD_NS + "tab":
        return "\t"
    if node.tag in (WORD_NS + "br", WORD_NS + "cr"):
        return "\n"
    result = "".join(_word_text(child) for child in node)
    if node.tag == WORD_NS + "p":
        properties = node.find(WORD_NS + "pPr")
        if properties is not None and result.strip():
            style = properties.find(WORD_NS + "pStyle")
            heading = re.fullmatch(r"Heading([1-6])", style.get(WORD_NS + "val", ""), re.I) if style is not None else None
            if heading:
                result = "#" * int(heading[1]) + " " + result
            elif properties.find(WORD_NS + "numPr") is not None:
                result = "- " + result
        return result + "\n"
    if node.tag == WORD_NS + "tc":
        return result.rstrip("\n") + "\t"
    if node.tag == WORD_NS + "tr":
        return result.rstrip("\t") + "\n"
    return result


def extract_docx(path: Path) -> Extraction:
    parts: list[str] = []
    try:
        with ZipFile(path) as archive:
            # Include each header/footer once, plus notes. Never follow external
            # relationships or interpret macros, fields, images or altChunk.
            names = ["word/document.xml"] + sorted(
                name for name in archive.namelist()
                if re.fullmatch(r"word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml", name)
            )
            total = 0
            for name in names:
                total += archive.getinfo(name).file_size
                if total > MAX_DOCX_XML_BYTES:
                    return Extraction("\n".join(parts), "DOCX text exceeds extraction limit")
                raw = archive.read(name)
                if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
                    return Extraction("\n".join(parts), "unsupported DOCX XML declarations")
                root = ET.fromstring(raw)
                for node in root.iter():
                    node.tag = node.tag.replace(STRICT_WORD_NS, WORD_NS)
                    node.attrib = {key.replace(STRICT_WORD_NS, WORD_NS): value for key, value in node.attrib.items()}
                if name == "word/document.xml" and (root.tag != WORD_NS + "document" or root.find(WORD_NS + "body") is None):
                    return Extraction(issue="invalid DOCX document XML")
                if name in ("word/footnotes.xml", "word/endnotes.xml"):
                    # Separator notes use nonpositive IDs and are not body text.
                    text = "".join(_word_text(note) for note in root if int(note.get(WORD_NS + "id", "0")) > 0)
                else:
                    text = _word_text(root)
                if text.strip():
                    parts.append(text.strip())
    except Exception:
        # Parser exceptions can contain document text. Expose only fixed labels.
        return Extraction("\n".join(parts), "cannot extract DOCX text")
    return Extraction("\n".join(parts))


def extract_pdf(path: Path) -> Extraction:
    from pypdf import PdfReader

    parts: list[str] = []
    issue = None
    logger = logging.getLogger("pypdf")
    previous_level = logger.level
    logger.setLevel(logging.CRITICAL + 1)  # Parser messages can quote private content.
    try:
        with path.open("rb") as source:
            reader = PdfReader(source)
            if reader.is_encrypted:
                return Extraction(issue="encrypted PDF")
            for page in reader.pages:
                try:
                    text = page.extract_text() or ""
                    if text.strip():
                        parts.append(text.strip())
                except Exception:
                    issue = "cannot extract some PDF pages"
    except Exception:
        issue = "cannot extract PDF text"
    finally:
        logger.setLevel(previous_level)
    return Extraction("\n\n".join(parts), issue)


def extract_doc(path: Path) -> Extraction:
    reader = shutil.which("libreoffice") or shutil.which("soffice")
    if reader is None:
        return Extraction(issue="DOC reader unavailable (install LibreOffice)")
    try:
        with tempfile.TemporaryDirectory(prefix="ttree-doc-") as temporary:
            work = Path(temporary)
            profile = work / "profile"
            user = profile / "user"
            user.mkdir(parents=True)
            # Use a separate profile. Disable macros and external link updates.
            (user / "registrymodifications.xcu").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<oor:items xmlns:oor="http://openoffice.org/2001/registry">'
                '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
                '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>'
                '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>'
                '<prop oor:name="DisableActiveContent" oor:op="fuse"><value>true</value></prop></item>'
                '<item oor:path="/org.openoffice.Office.Writer/Content/Update">'
                '<prop oor:name="Link" oor:op="fuse"><value>2</value></prop>'
                '<prop oor:name="Field" oor:op="fuse"><value>false</value></prop>'
                '<prop oor:name="Chart" oor:op="fuse"><value>false</value></prop></item>'
                '</oor:items>', encoding="utf-8",
            )
            # A private copy prevents lock files beside the original document.
            source = work / "input.doc"
            shutil.copyfile(path, source)
            returncode = _run_doc_reader(
                [reader, f"-env:UserInstallation={profile.as_uri()}", "--headless",
                 "--nologo", "--nodefault", "--norestore", "--convert-to",
                 "txt:Text (encoded):UTF8", "--outdir", str(work), str(source)],
            )
            output = work / "input.txt"
            if returncode != 0 or not output.is_file():
                return Extraction(issue="cannot extract DOC text")
            return Extraction(output.read_text(encoding="utf-8-sig").strip())
    except subprocess.TimeoutExpired:
        return Extraction(issue="DOC reader timed out")
    except (OSError, UnicodeError):
        return Extraction(issue="cannot extract DOC text")


def _run_doc_reader(command: list[str]) -> int:
    with subprocess.Popen(
        command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=os.name == "posix",
    ) as process:
        try:
            return process.wait(timeout=DOC_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            # LibreOffice can spawn a child. Kill our own process group on Unix.
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                process.kill()
            process.wait()
            raise


def extract_document(path: Path) -> Extraction:
    return {".docx": extract_docx, ".pdf": extract_pdf, ".doc": extract_doc}[path.suffix.lower()](path)
