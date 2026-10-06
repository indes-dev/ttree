"""TASK-002 DOCX probes. Synthetic fixtures only.

Usage: python probe_docx.py {make|run} WORKDIR CASE
Each case builds one fixture in WORKDIR, runs extract_docx() in-process and
prints the issue label, text length and peak RSS. Run each case under
run_bounded.sh so that hostile cases stay bounded by the OS.
"""

import resource
import struct
import sys
import time
import zlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from ttree.documents import WORD_NS, extract_docx

W = WORD_NS[1:-1]


def document(body: str) -> str:
    return f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'


def para(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def write(path: Path, members: dict[str, bytes | str], compression=ZIP_DEFLATED) -> None:
    with ZipFile(path, "w", compression) as archive:
        for name, data in members.items():
            archive.writestr(name, data)


def case_baseline(path):
    write(path, {"word/document.xml": document(para("Hello DOCX"))})


def case_utf16_entity(path):
    # DTD with an internal entity, encoded as UTF-16: the ASCII guard cannot see it.
    xml = (f'<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE d [<!ENTITY e "EXPANDED">]>'
           + document(para("&e;")))
    write(path, {"word/document.xml": xml.encode("utf-16")})


def case_utf16_laughs(path):
    # Classic exponential expansion, UTF-16 encoded.
    ents = ['<!ENTITY a0 "LOLLOLLOLLOL">'] + [
        f'<!ENTITY a{i} "' + f"&a{i-1};" * 10 + '">' for i in range(1, 10)]
    xml = (f'<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE d [{"".join(ents)}]>'
           + document(para("&a9;")))
    write(path, {"word/document.xml": xml.encode("utf-16")})


def case_utf16_quadratic(path):
    # One large entity referenced many times (quadratic blowup), UTF-16 encoded.
    xml = (f'<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE d [<!ENTITY a "{"x" * 100_000}">]>'
           + document("<w:p><w:r><w:t>" + "&a;" * 20_000 + "</w:t></w:r></w:p>"))
    write(path, {"word/document.xml": xml.encode("utf-16")})


def case_utf16_external(path):
    # External entity pointing at a local file: must never be read.
    xml = (f'<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE d [<!ENTITY x SYSTEM "file:///etc/hostname">]>'
           + document(para("&x;")))
    write(path, {"word/document.xml": xml.encode("utf-16")})


def case_utf8_entity(path):
    xml = '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY e "EXPANDED">]>' + document(para("&e;"))
    write(path, {"word/document.xml": xml})


def case_lowercase_doctype(path):
    # Guard uppercases; confirm case-insensitive detection still works.
    xml = '<?xml version="1.0"?><!doctype d>' + document(para("x"))
    write(path, {"word/document.xml": xml})


def case_duplicate_members(path):
    # Duplicate header names: namelist() lists both; read() returns the last one.
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document(para("Body")))
        archive.writestr("word/header1.xml", f'<w:hdr xmlns:w="{W}">{para("First header")}</w:hdr>')
        archive.writestr("word/header1.xml", f'<w:hdr xmlns:w="{W}">{para("Second header")}</w:hdr>')


def case_lying_size(path):
    # Central directory declares 100 bytes; the deflate stream expands to ~200 MiB.
    payload = document("<w:p><w:r><w:t>" + "A" * (200 * 1024 * 1024) + "</w:t></w:r></w:p>").encode()
    write(path, {"word/document.xml": payload})
    data = bytearray(path.read_bytes())
    # Patch uncompressed size in local header (offset 22) and central directory (offset 24).
    struct.pack_into("<I", data, 22, 100)
    central = data.rfind(b"PK\x01\x02")
    struct.pack_into("<I", data, central + 24, 100)
    path.write_bytes(bytes(data))


def case_lying_size_2g(path):
    # Same as lying_size, but the stream expands to ~2 GiB from a ~2 MiB file.
    # Built with a streaming compressor so that the fixture itself stays cheap.
    head = (f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>').encode()
    tail = b"</w:t></w:r></w:p></w:body></w:document>"
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    chunks = [compressor.compress(head)]
    block = b"A" * (16 * 1024 * 1024)
    crc = zlib.crc32(head)
    for _ in range(127):  # 127 x 16 MiB = 2032 MiB
        chunks.append(compressor.compress(block))
        crc = zlib.crc32(block, crc)
    chunks.append(compressor.compress(tail))
    crc = zlib.crc32(tail, crc)
    chunks.append(compressor.flush())
    stream = b"".join(chunks)
    name = b"word/document.xml"
    declared = 100
    local = struct.pack("<4sHHHHHIIIHH", b"PK\x03\x04", 20, 0, 8, 0, 0, crc, len(stream), declared, len(name), 0) + name
    central = struct.pack("<4sHHHHHHIIIHHHHHII", b"PK\x01\x02", 20, 20, 0, 8, 0, 0, crc, len(stream), declared,
                          len(name), 0, 0, 0, 0, 0, 0) + name
    end = struct.pack("<4sHHHHIIH", b"PK\x05\x06", 0, 0, 1, 1, len(central), len(local) + len(stream), 0)
    path.write_bytes(local + stream + central + end)


def case_bomb_under_limit(path):
    # ~31 MiB of tiny paragraphs: maximal element count within the 32 MiB budget.
    unit = para("a")
    body = unit * ((31 * 1024 * 1024) // len(unit))
    write(path, {"word/document.xml": document(body)})


def case_deep_nesting(path):
    depth = 2_000_000
    body = "<w:p>" + "<w:r>" * depth + "<w:t>deep</w:t>" + "</w:r>" * depth + "</w:p>"
    write(path, {"word/document.xml": document(body)})


def case_moderate_nesting(path):
    # Nesting just above Python's default recursion limit.
    depth = 1500
    body = "<w:p>" + "<w:r>" * depth + "<w:t>deep</w:t>" + "</w:r>" * depth + "</w:p>"
    write(path, {"word/document.xml": document(body)})


def case_many_entries(path):
    # Large central directory of empty members (cost bounded by file size).
    with ZipFile(path, "w", ZIP_STORED) as archive:
        archive.writestr("word/document.xml", document(para("x")))
        for index in range(200_000):
            archive.writestr(f"z/{index}", b"")


def case_missing_document(path):
    write(path, {"word/header1.xml": f'<w:hdr xmlns:w="{W}">{para("h")}</w:hdr>'})


def case_external_relationship(path):
    write(path, {
        "word/document.xml": document(para("Body") + '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                                      '<w:r><w:instrText>INCLUDETEXT "http://127.0.0.1:9/x"</w:instrText></w:r>'
                                      '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'),
        "word/_rels/document.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                                        '<Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                                        'Target="http://127.0.0.1:9/i.png" TargetMode="External"/></Relationships>',
        "word/embeddings/oleObject1.bin": b"\xd0\xcf\x11\xe0" + b"\0" * 64,
    })


def case_ordering(path):
    # Body text, table, then notes; headers/footers appear after the body.
    write(path, {
        "word/document.xml": document(para("Body1") + '<w:tbl><w:tr><w:tc>' + para("Cell") + '</w:tc></w:tr></w:tbl>' + para("Body2")),
        "word/footer2.xml": f'<w:ftr xmlns:w="{W}">{para("Footer2")}</w:ftr>',
        "word/footer10.xml": f'<w:ftr xmlns:w="{W}">{para("Footer10")}</w:ftr>',
        "word/endnotes.xml": f'<w:endnotes xmlns:w="{W}"><w:endnote w:id="-1">{para("Sep")}</w:endnote><w:endnote w:id="2">{para("End")}</w:endnote></w:endnotes>',
        "word/comments.xml": f'<w:comments xmlns:w="{W}"><w:comment w:id="0">{para("Comment")}</w:comment></w:comments>',
    })


def case_strict_ooxml(path):
    strict = "http://purl.oclc.org/ooxml/wordprocessingml/main"
    write(path, {"word/document.xml": f'<w:document xmlns:w="{strict}"><w:body>{para("Strict text")}</w:body></w:document>'})


def case_textbox_alternate_content(path):
    # Word stores a text box twice: DrawingML in mc:Choice and VML in mc:Fallback.
    box = f"<w:txbxContent>{para('BoxText')}</w:txbxContent>"
    write(path, {"word/document.xml": document(
        para("Body") + '<w:p><w:r><mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
        f'<mc:Choice Requires="wps"><w:drawing><wps:txbx xmlns:wps="urn:wps">{box}</wps:txbx></w:drawing></mc:Choice>'
        f'<mc:Fallback><w:pict><v:textbox xmlns:v="urn:schemas-microsoft-com:vml">{box}</v:textbox></w:pict></mc:Fallback>'
        '</mc:AlternateContent></w:r></w:p>')})


def case_fields_and_revisions(path):
    write(path, {"word/document.xml": document(
        '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> DATE \\@ "yyyy" </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>FieldResult</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
        '<w:p><w:del><w:r><w:delText>DeletedText</w:delText></w:r></w:del><w:ins><w:r><w:t>Inserted</w:t></w:r></w:ins></w:p>'
        '<w:p><w:moveFrom><w:r><w:t>MovedText</w:t></w:r></w:moveFrom></w:p>'
        '<w:p><w:moveTo><w:r><w:t>MovedText</w:t></w:r></w:moveTo></w:p>'
        '<w:p><w:r><w:drawing><wp:docPr xmlns:wp="urn:wp" id="1" name="Picture" descr="AltText"/></w:drawing></w:r></w:p>')})


def case_bad_note_id(path):
    write(path, {
        "word/document.xml": document(para("Body")),
        "word/footnotes.xml": f'<w:footnotes xmlns:w="{W}"><w:footnote w:id="x">{para("Bad id")}</w:footnote></w:footnotes>',
    })


def case_truncated_zip(path):
    case_baseline(path)
    data = path.read_bytes()
    path.write_bytes(data[: len(data) // 2])


CASES = {name[5:]: fn for name, fn in globals().items() if name.startswith("case_")}


def main():
    # "make" builds the fixture (trusted, unbounded); "run" extracts it (bounded).
    mode, work, case = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    work.mkdir(parents=True, exist_ok=True)
    path = work / f"{case}.docx"
    if mode == "make":
        CASES[case](path)
        return
    start = time.monotonic()
    result = extract_docx(path)
    elapsed = time.monotonic() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    preview = result.text[:60].replace("\n", "\\n")
    print(f"case={case} file_bytes={path.stat().st_size} issue={result.issue!r} "
          f"text_chars={len(result.text)} seconds={elapsed:.2f} peak_rss_mib={peak} preview={preview!r}")


if __name__ == "__main__":
    main()
