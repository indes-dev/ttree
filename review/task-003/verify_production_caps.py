"""Live installed-wheel caps, synthetic files and cross-root continuation."""

from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def xml(local, padding):
    return f'<w:{local} xmlns:w="{WORD}">' + padding + f"</w:{local}>"


def main(python, work):
    work.mkdir(parents=True, exist_ok=False)
    okay = work / "okay.txt"
    okay.write_text("Hello, world!")
    checks = []

    def check(name, path, expected, *options):
        start = time.monotonic()
        result = subprocess.run(
            [
                str(python),
                "-m",
                "ttree.cli",
                "--json",
                "--strict",
                *options,
                str(path),
                str(okay),
            ],
            capture_output=True,
            text=True,
            timeout=25,
            env={**os.environ, "TMPDIR": str(work)},
        )
        document = json.loads(result.stdout)
        first, next_root = document["roots"]
        assert result.returncode == 3 and not result.stderr
        assert first["status"] == expected and first["tokens"] is None
        assert not first["complete"] and first["bytes"] == path.stat().st_size
        assert next_root["tokens"] == 4 and next_root["complete"]
        assert document["total"]["tokens"] == 4 and not document["total"]["complete"]
        checks.append(
            {
                "case": name,
                "status": first["status"],
                "exit": result.returncode,
                "seconds": round(time.monotonic() - start, 4),
                "input_bytes": path.stat().st_size,
                "next_root_counted": True,
            }
        )

    started = time.monotonic()
    oversized = work / "oversized.txt"
    with oversized.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    check("actual_input_64MiB_plus_one", oversized, "too_large")
    text = work / "characters.txt"
    text.write_text("x" * 1_000_001)
    check("text_characters_1000001", text, "too_large")
    path = work / "aggregate.docx"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            xml("document", "<w:body>" + " " * (3 * 1024 * 1024) + "</w:body>"),
        )
        archive.writestr("word/header1.xml", xml("hdr", " " * (3 * 1024 * 1024)))
        archive.writestr("word/footer1.xml", xml("ftr", " " * (3 * 1024 * 1024)))
    check("actual_XML_aggregate_over_8MiB_each_part_below_4MiB", path, "too_large")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            xml("document", "<w:body>" + "<w:r/>" * 100_000 + "</w:body>"),
        )
    check("actual_XML_elements_over_100000", path, "too_large")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            xml(
                "document",
                "<w:body><w:p><w:r><w:t>"
                + "x" * 1_000_001
                + "</w:t></w:r></w:p></w:body>",
            ),
        )
    check("DOCX_characters_1000001", path, "too_large")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", xml("document", "<w:body/>"))
        for index in range(4096):
            archive.writestr(f"unused/{index}", b"")
    check("actual_ZIP_members_4097", path, "too_large")
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "word/document.xml",
            xml("document", "<w:body>" + " " * (5 * 1024 * 1024) + "</w:body>"),
        )
    raw = bytearray(path.read_bytes())
    central = raw.index(b"PK\x01\x02")
    struct.pack_into("<I", raw, central + 24, 32)
    struct.pack_into("<I", raw, 22, 32)
    path.write_bytes(raw)
    # ZIP's real CRC validation rejects the shortened metadata. This does not
    # claim that all 5 MiB were returned by this lying-size member read.
    check("lying_ZIP_uncompressed_size_rejected_by_CRC", path, "failed")
    pdf = work / "pages.pdf"
    writer = PdfWriter()
    for _ in range(2001):
        writer.add_blank_page(300, 300)
    writer.write(pdf)
    check("actual_PDF_pages_2001", pdf, "too_large")
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    reference = writer._add_object(font)
    for _ in range(2):
        page = writer.add_blank_page(300, 300)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): reference})}
        )
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 20 200 Td (" + b"x " * 300_001 + b") Tj ET")
        page[NameObject("/Contents")] = writer._add_object(stream)
    writer.write(pdf)
    check("actual_PDF_characters_over_1000000", pdf, "too_large")
    check("lowered_positive_input_cap", text, "too_large", "--limit-input-bytes", "100")
    result = {
        "passed": True,
        "python": str(python),
        "cases": checks,
        "elapsed_seconds": round(time.monotonic() - started, 4),
    }
    (work / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
