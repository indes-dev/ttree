"""Bounded document extraction, called only inside a disposable worker.

Legacy DOC is deliberately unsupported pending native boundary adjudication.
There is no native subprocess, converter, fallback or external relationship fetch.
"""

from __future__ import annotations

import logging
import re
from xml.parsers import expat
from zipfile import ZipFile

from ttree.limits import CAPS


class Stop(Exception):
    def __init__(self, status):
        self.status = status


WORD_URIS = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def word_name(tag):
    uri, _, local = tag.rpartition("}")
    return local if uri in WORD_URIS else None


def word_attr(attrs, name):
    return next((value for key, value in attrs.items() if word_name(key) == name), "")


def xml_text(stream, name, metrics, budget):
    parser = expat.ParserCreate(namespace_separator="}")
    frames = []
    namespace = {}
    history = {}
    result = []
    body_seen = False
    part_bytes = 0
    expected = (
        "document"
        if name == "word/document.xml"
        else "hdr"
        if "/header" in name
        else "ftr"
        if "/footer" in name
        else "footnotes"
        if name == "word/footnotes.xml"
        else "endnotes"
    )

    def add_size(size):
        budget["characters"] += size
        if budget["characters"] > CAPS["characters"]:
            raise Stop("too_large")

    def start_namespace(prefix, uri):
        history.setdefault(prefix, []).append(namespace.get(prefix))
        namespace[prefix] = uri

    def end_namespace(prefix):
        previous = history[prefix].pop()
        if previous is None:
            namespace.pop(prefix, None)
        else:
            namespace[prefix] = previous

    def start(tag, attrs):
        nonlocal body_seen
        depth = len(frames) + 1
        budget["elements"] += 1
        metrics.update(
            xml_elements=budget["elements"],
            xml_depth_peak=max(metrics.get("xml_depth_peak", 0), depth),
        )
        if depth > CAPS["xml_depth"] or budget["elements"] > CAPS["xml_elements"]:
            raise Stop("too_large")
        local = word_name(tag)
        if depth == 1 and local != expected:
            raise Stop("failed")
        active = frames[-1]["active"] if frames else True
        if name == "word/document.xml" and depth == 2:
            active = local == "body"
            if active:
                body_seen = True
        if local in {"del", "moveFrom"}:
            active = False
        if local in {"footnote", "endnote"}:
            try:
                active = active and int(word_attr(attrs, "id") or "0") > 0
            except ValueError:
                raise Stop("failed") from None
        if frames and frames[-1]["tag"] == MC + "}AlternateContent":
            alternate = frames[-1]
            if tag == MC + "}Choice":
                required = attrs.get("Requires", "").split()
                supported = bool(required) and all(
                    namespace.get(prefix) in WORD_URIS for prefix in required
                )
                active = active and supported and not alternate["selected"]
            elif tag == MC + "}Fallback":
                active = active and not alternate["selected"]
            else:
                active = False
            if active:
                alternate["selected"] = True
        frame = {
            "tag": tag,
            "local": local,
            "active": active,
            "selected": False,
            "chunks": [],
            "heading": None,
            "list": False,
        }
        if active and local in {"pStyle", "numPr"}:
            paragraph = next(
                (item for item in reversed(frames) if item["local"] == "p"), None
            )
            if paragraph is not None:
                if local == "numPr":
                    paragraph["list"] = True
                else:
                    style = re.fullmatch(
                        r"Heading([1-6])", word_attr(attrs, "val"), re.I
                    )
                    if style:
                        paragraph["heading"] = int(style[1])
        frames.append(frame)

    def text(data):
        if frames and frames[-1]["active"] and frames[-1]["local"] == "t":
            add_size(len(data))
            frames[-1]["chunks"].append(data)

    def end(tag):
        frame = frames.pop()
        if not frame["active"]:
            return
        value = "".join(frame["chunks"])
        local = frame["local"]
        if local == "tab":
            value = "\t"
            add_size(1)
        elif local in {"br", "cr"}:
            value = "\n"
            add_size(1)
        elif local == "p":
            prefix = (
                ("#" * frame["heading"] + " ")
                if frame["heading"] and value.strip()
                else ("- " if frame["list"] and value.strip() else "")
            )
            value = prefix + value + "\n"
            add_size(len(prefix) + 1)
        elif local == "tc":
            value = value.rstrip("\n") + "\t"
            add_size(1)
        elif local == "tr":
            value = value.rstrip("\t") + "\n"
            add_size(1)
        if frames:
            frames[-1]["chunks"].append(value)
        else:
            result.append(value)

    def reject(*args):
        raise Stop("failed")

    parser.StartNamespaceDeclHandler = start_namespace
    parser.EndNamespaceDeclHandler = end_namespace
    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = text
    parser.StartDoctypeDeclHandler = reject
    parser.EntityDeclHandler = reject
    parser.ExternalEntityRefHandler = reject
    while True:
        block = stream.read(
            min(
                65536,
                CAPS["xml_part_bytes"] - part_bytes + 1,
                CAPS["xml_total_bytes"] - budget["bytes"] + 1,
            )
        )
        if not block:
            break
        part_bytes += len(block)
        budget["bytes"] += len(block)
        metrics["actual_xml_bytes"] = budget["bytes"]
        if (
            part_bytes > CAPS["xml_part_bytes"]
            or budget["bytes"] > CAPS["xml_total_bytes"]
        ):
            raise Stop("too_large")
        parser.Parse(block, False)
    parser.Parse(b"", True)
    if name == "word/document.xml" and not body_seen:
        raise Stop("failed")
    return "".join(result).strip()


def docx(source, metrics):
    budget = {"bytes": 0, "elements": 0, "characters": 0}
    parts = []
    with ZipFile(source) as archive:
        names = archive.namelist()
        if len(names) > CAPS["zip_members"]:
            raise Stop("too_large")
        if len(names) != len(set(names)):
            raise Stop("failed")
        selected = ["word/document.xml"] + sorted(
            name
            for name in names
            if re.fullmatch(
                r"word/(?:header\d+|footer\d+|footnotes|endnotes)\.xml", name
            )
        )
        for name in selected:
            with archive.open(name) as stream:
                text = xml_text(stream, name, metrics, budget)
            if text:
                parts.append(text)
    return "\n".join(parts), "counted"


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
