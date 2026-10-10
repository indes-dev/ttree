"""Bounded document extraction, called only inside a disposable worker.

Legacy DOC uses static OLE/Word text reading.
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


def doc(source, metrics):
    """Read Word 97-2003 piece-table text without invoking an Office runtime.

    MS-DOC 2.4.1, FibBase, FibRgLw97, FibRgFcLcb97, Clx and FcCompressed:
    https://learn.microsoft.com/en-us/openspecs/office_file_formats/ms-doc/01d5d8c4-cf9c-4ef9-80fd-439e763cfe01
    OLE parsing stays inside the disposable resource-limited worker.
    """
    import olefile

    source.seek(0)
    if source.read(8) != olefile.MAGIC:
        raise Stop("unsupported")
    source.seek(0)
    with olefile.OleFileIO(source, raise_defects=olefile.DEFECT_INCORRECT) as ole:

        def stream(name):
            if ole.get_size(name) > CAPS["input_bytes"]:
                raise Stop("too_large")
            with ole.openstream(name) as value:
                data = value.read(CAPS["input_bytes"] + 1)
            if len(data) > CAPS["input_bytes"]:
                raise Stop("too_large")
            return data

        word = stream("WordDocument")
        text, status = doc_text(word, stream, metrics)
        return text, "partial" if ole.parsing_issues else status


def doc_text(word, stream, metrics):
    """Decode only explicitly addressed text; never interpret objects or fields."""

    def number(data, offset, size=4):
        if offset < 0 or offset + size > len(data):
            raise Stop("failed")
        return int.from_bytes(data[offset : offset + size], "little")

    if number(word, 0, 2) != 0xA5EC:
        raise Stop("unsupported")
    if number(word, 2, 2) not in {0xC1, 0xD9, 0x101, 0x10C, 0x112}:
        raise Stop("unsupported")
    flags = number(word, 10, 2)
    if flags & 0x100:
        raise Stop("encrypted")
    csw = number(word, 32, 2)
    if csw != 14:
        raise Stop("failed")
    lw = 34 + 2 * csw
    if number(word, lw, 2) != 22:
        raise Stop("failed")
    lw += 2
    counts = [number(word, lw + i * 4) for i in (3, 4, 5, 7, 8, 9, 10)]
    total = sum(counts)
    if total > CAPS["characters"]:
        raise Stop("too_large")
    pairs = lw + 22 * 4
    if number(word, pairs, 2) < 93:
        raise Stop("failed")
    fc = pairs + 2 + 33 * 8
    start, size = number(word, fc), number(word, fc + 4)
    table = stream("1Table" if flags & 0x200 else "0Table")
    if start + size > len(table) or size < 5:
        raise Stop("failed")
    clx = table[start : start + size]
    pos = 0
    while pos < len(clx) and clx[pos] == 1:
        pos += 3 + number(clx, pos + 1, 2)
    if pos + 5 > len(clx) or clx[pos] != 2:
        raise Stop("failed")
    length = number(clx, pos + 1)
    if length < 4 or (length - 4) % 12 or pos + 5 + length != len(clx):
        raise Stop("failed")
    pieces = (length - 4) // 12
    if pieces > CAPS["characters"]:
        raise Stop("too_large")
    plc = clx[pos + 5 :]
    cp = [number(plc, i * 4) for i in range(pieces + 1)]
    if cp[0] != 0 or cp[-1] < total or any(a >= b for a, b in zip(cp, cp[1:])):
        raise Stop("failed")
    result = []
    for i in range(pieces):
        if cp[i] >= total:
            break
        count = min(cp[i + 1], total) - cp[i]
        encoded = number(plc, 4 * (pieces + 1) + i * 8 + 2)
        if encoded & 0x80000000:
            raise Stop("failed")
        compressed = bool(encoded & 0x40000000)
        offset = encoded & 0x3FFFFFFF
        if compressed:
            if offset % 2:
                raise Stop("failed")
            offset //= 2
        end = offset + count * (1 if compressed else 2)
        if offset < pairs + 2 + 93 * 8 or end > len(word):
            raise Stop("failed")
        raw = word[offset:end]
        if compressed:
            # MS-DOC maps only its listed exceptional bytes through CP1252;
            # undefined CP1252 entries retain their original Unicode codepoint.
            text = "".join(
                bytes([b]).decode("cp1252")
                if b not in {0x80, 0x81, 0x8D, 0x8E, 0x8F, 0x90, 0x9D, 0x9E}
                else chr(b)
                for b in raw
            )
        else:
            # Decode after joining pieces: a UTF-16 surrogate pair may straddle
            # adjacent piece boundaries. Preserve code units until then.
            text = raw.decode("utf-16-le", errors="surrogatepass")
        result.append(text)
    text = (
        "".join(result).encode("utf-16-le", errors="surrogatepass").decode("utf-16-le")
    )
    metrics["doc_pieces"] = pieces
    # Fields contain instruction text, separator, then saved display text.
    # Count only the display text. Never evaluate a field or follow its target.
    fields = []
    visible = []
    mapping = {
        "\r": "\n",
        "\x07": "\t",
        "\x0b": "\n",
        "\x0c": "\n",
        "\x1e": "\u2011",
        "\x1f": "\u00ad",
    }
    for char in text:
        if char == "\x13":
            fields.append(False)
        elif char == "\x14":
            if not fields or fields[-1]:
                raise Stop("failed")
            fields[-1] = True
        elif char == "\x15":
            if not fields:
                raise Stop("failed")
            fields.pop()
        elif all(fields) and (ord(char) >= 32 or char in mapping or char == "\t"):
            visible.append(mapping.get(char, char))
    if fields:
        raise Stop("failed")
    return "".join(visible).strip(), "counted"
