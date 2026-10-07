"""Bounded document extraction, called only inside a disposable worker.

Legacy DOC is deliberately unsupported pending native boundary adjudication.
There is no native subprocess, converter, fallback or external relationship fetch.
"""

from __future__ import annotations

import logging
from xml.parsers import expat
from zipfile import ZipFile

from ttree.limits import CAPS


class Stop(Exception):
    def __init__(self, status):
        self.status = status


def docx(source, metrics):
    chunks = []
    characters = elements = actual = 0
    with ZipFile(source) as archive:
        names = archive.namelist()
        if len(names) > CAPS["zip_members"]:
            raise Stop("too_large")
        if len(names) != len(set(names)):
            raise Stop("failed")
        selected = ["word/document.xml"] + sorted(
            n
            for n in names
            if n.startswith("word/")
            and (
                n.startswith(("word/header", "word/footer"))
                or n in ("word/footnotes.xml", "word/endnotes.xml")
            )
            and n.endswith(".xml")
        )
        for name in selected:
            parser = expat.ParserCreate(namespace_separator="}")
            depth = 0
            text_depth = 0
            part_bytes = 0

            def start(tag, attrs):
                nonlocal depth, elements, text_depth
                depth += 1
                elements += 1
                metrics.update(
                    xml_elements=elements,
                    xml_depth_peak=max(metrics.get("xml_depth_peak", 0), depth),
                )
                if depth > CAPS["xml_depth"] or elements > CAPS["xml_elements"]:
                    raise Stop("too_large")
                if tag.endswith("}t"):
                    text_depth = depth

            def end(tag):
                nonlocal depth, text_depth
                if depth == text_depth:
                    text_depth = 0
                if tag.endswith("}p"):
                    append("\n")
                depth -= 1

            def append(data):
                nonlocal characters
                characters += len(data)
                if characters > CAPS["characters"]:
                    raise Stop("too_large")
                chunks.append(data)

            def text(data):
                if text_depth:
                    append(data)

            def reject(*args):
                raise Stop("failed")

            parser.StartElementHandler = start
            parser.EndElementHandler = end
            parser.CharacterDataHandler = text
            parser.StartDoctypeDeclHandler = reject
            parser.EntityDeclHandler = reject
            parser.ExternalEntityRefHandler = reject
            with archive.open(name) as stream:
                while True:
                    block = stream.read(
                        min(
                            65536,
                            CAPS["xml_part_bytes"] - part_bytes + 1,
                            CAPS["xml_total_bytes"] - actual + 1,
                        )
                    )
                    if not block:
                        break
                    part_bytes += len(block)
                    actual += len(block)
                    metrics["actual_xml_bytes"] = actual
                    if (
                        part_bytes > CAPS["xml_part_bytes"]
                        or actual > CAPS["xml_total_bytes"]
                    ):
                        raise Stop("too_large")
                    parser.Parse(block, False)
                parser.Parse(b"", True)
            chunks.append("\n")
    return "".join(chunks).strip(), "counted"


def pdf(source, metrics):
    from pypdf import PdfReader

    class Warnings(logging.Handler):
        def emit(self, record):
            # Count without formatting record arguments/document fragments.
            metrics["pdf_warnings"] = metrics.get("pdf_warnings", 0) + 1

    logger = logging.getLogger("pypdf")
    previous = logger.level, logger.propagate, logger.handlers[:]
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    logger.handlers = [Warnings(logging.WARNING)]
    parts = []
    status = "counted"
    chars = 0
    try:
        reader = PdfReader(source)
        if reader.is_encrypted:
            if not reader.decrypt(""):
                raise Stop("encrypted")
        if len(reader.pages) > CAPS["pdf_pages"]:
            raise Stop("too_large")
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
                chars += len(text)
                if chars > CAPS["characters"]:
                    raise Stop("too_large")
                parts.append(text)
            except Stop:
                raise
            except Exception:
                status = "partial"
        if metrics.get("pdf_warnings"):
            status = "partial"
    finally:
        logger.setLevel(previous[0])
        logger.propagate, logger.handlers = previous[1:]
    return "\n\n".join(parts), status
