"""TASK-002 PDF probes. Synthetic fixtures only.

Usage: python probe_pdf.py {make|run} WORKDIR CASE
"make" writes the fixture (trusted, unbounded). "run" calls extract_pdf() and
prints the issue label, text length, time and peak RSS; run it under run_bounded.sh.
"""

import resource
import sys
import time
import zlib
from pathlib import Path


def build(objects: dict[int, bytes], root: int = 1, trailer_extra: bytes = b"") -> bytes:
    """Serialize numbered objects into a PDF with a correct xref table."""
    out = bytearray(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref = len(out)
    size = max(objects) + 1
    out += b"xref\n0 %d\n0000000000 65535 f \n" % size
    for number in range(1, size):
        out += (b"%010d 00000 n \n" % offsets[number]) if number in offsets else b"0000000000 65535 f \n"
    out += b"trailer\n<< /Size %d /Root %d 0 R %s>>\nstartxref\n%d\n%%%%EOF\n" % (size, root, trailer_extra, xref)
    return bytes(out)


def stream(data: bytes, extra: bytes = b"") -> bytes:
    return b"<< /Length %d %s>>\nstream\n" % (len(data), extra) + data + b"\nendstream"


FONT = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"


def text_page_objects(content: bytes, first: int = 1) -> dict[int, bytes]:
    return {
        first: b"<< /Type /Catalog /Pages %d 0 R >>" % (first + 1),
        first + 1: b"<< /Type /Pages /Kids [%d 0 R] /Count 1 >>" % (first + 2),
        first + 2: b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>" % (first + 1, first + 3, first + 4),
        first + 3: FONT,
        first + 4: stream(content),
    }


def case_baseline(path):
    path.write_bytes(build(text_page_objects(b"BT /F1 12 Tf 20 200 Td (Readable PDF text) Tj ET")))


def case_flate_bomb(path):
    # Content stream that inflates to ~1 GiB of text-show operators.
    unit = b"BT /F1 12 Tf 20 200 Td (AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA) Tj ET\n"
    compressor = zlib.compressobj(9)
    block = unit * ((16 * 1024 * 1024) // len(unit))
    data = b"".join(compressor.compress(block) for _ in range(64)) + compressor.flush()
    objects = text_page_objects(b"")
    objects[5] = stream(data, b"/Filter /FlateDecode ")
    path.write_bytes(build(objects))


def case_page_tree_amplification(path):
    # Six levels of /Pages nodes, each listing the next level 10 times:
    # 10**6 leaf references from a file of a few kilobytes.
    content = b"BT /F1 12 Tf 20 200 Td (" + b"Amplified text " * 20 + b") Tj ET"
    objects = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: FONT, 4: stream(content)}
    levels = 6
    for level in range(levels):
        number = 2 if level == 0 else 10 + level
        child = 10 + level + 1 if level < levels - 1 else 20
        kids = b" ".join(b"%d 0 R" % child for _ in range(10))
        objects[number] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, 10 ** (levels - level))
    objects[20] = b"<< /Type /Page /MediaBox [0 0 300 300] /Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"
    path.write_bytes(build(objects))


def case_many_pages(path):
    # 20,000 distinct small text pages (file size grows linearly).
    objects = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: FONT,
               4: stream(b"BT /F1 12 Tf 20 200 Td (Page text) Tj ET")}
    pages = 20_000
    kids = []
    for index in range(pages):
        number = 10 + index
        kids.append(b"%d 0 R" % number)
        objects[number] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"
    objects[2] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(kids), pages)
    path.write_bytes(build(objects))


def case_operator_flood(path):
    # ~8 MiB uncompressed of tiny text operators on one page (CPU cost of extraction).
    unit = b"BT /F1 1 Tf 1 1 Td (x) Tj ET\n"
    data = zlib.compress(unit * ((8 * 1024 * 1024) // len(unit)), 9)
    objects = text_page_objects(b"")
    objects[5] = stream(data, b"/Filter /FlateDecode ")
    path.write_bytes(build(objects))


def _shared_flood(path, pages):
    # `pages` distinct page objects that all reference one ~21 KB compressed
    # operator-flood stream. Each page re-runs the expensive extraction.
    unit = b"BT /F1 1 Tf 1 1 Td (x) Tj ET\n"
    data = zlib.compress(unit * ((8 * 1024 * 1024) // len(unit)), 9)
    objects = {1: b"<< /Type /Catalog /Pages 2 0 R >>", 3: FONT, 4: stream(data, b"/Filter /FlateDecode ")}
    kids = []
    for index in range(pages):
        number = 10 + index
        kids.append(b"%d 0 R" % number)
        objects[number] = b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"
    objects[2] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(kids), pages)
    path.write_bytes(build(objects))


def case_shared_flood_2(path):
    _shared_flood(path, 2)


def case_shared_flood_4(path):
    _shared_flood(path, 4)


def case_shared_flood_1000(path):
    _shared_flood(path, 1000)


def case_corrupt_xref(path):
    data = bytearray(build(text_page_objects(b"BT /F1 12 Tf 20 200 Td (Recovered text) Tj ET")))
    index = data.find(b"xref\n")
    data[index + 5: index + 40] = b"9" * 35
    path.write_bytes(bytes(data))


def case_damaged_page(path):
    # Second page has a broken content stream (wrong length, garbage filter).
    objects = {1: b"<< /Type /Catalog /Pages 2 0 R >>",
               2: b"<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>",
               3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
               4: FONT, 5: stream(b"BT /F1 12 Tf 20 200 Td (Good page) Tj ET"),
               6: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 4 0 R >> >> /Contents 7 0 R >>",
               7: b"<< /Length 50 /Filter /FlateDecode >>\nstream\nnot-zlib-data\nendstream"}
    path.write_bytes(build(objects))


def case_truncated(path):
    data = build(text_page_objects(b"BT /F1 12 Tf 20 200 Td (Truncated) Tj ET"))
    path.write_bytes(data[: len(data) * 2 // 3])


def case_type3_font(path):
    # Type3 font without ToUnicode: glyph names only.
    objects = text_page_objects(b"BT /F1 12 Tf 20 200 Td (abc) Tj ET")
    objects[4] = (b"<< /Type /Font /Subtype /Type3 /FontBBox [0 0 1 1] /FontMatrix [1 0 0 1 0 0] "
                  b"/CharProcs << /a 6 0 R >> /Encoding << /Differences [97 /a /a /a] >> /FirstChar 97 /LastChar 99 /Widths [1 1 1] >>")
    objects[6] = stream(b"1 0 0 0 1 1 d1")
    path.write_bytes(build(objects))


def case_identity_cid_font(path):
    # Composite font with Identity-H and no ToUnicode: codes cannot map to text.
    objects = text_page_objects(b"BT /F1 12 Tf 20 200 Td <00410042> Tj ET")
    objects[4] = (b"<< /Type /Font /Subtype /Type0 /BaseFont /X /Encoding /Identity-H "
                  b"/DescendantFonts [6 0 R] >>")
    objects[6] = b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /X /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> >>"
    path.write_bytes(build(objects))


def _encrypted(path, user_password):
    from pypdf import PdfReader, PdfWriter
    plain = path.with_suffix(".plain.pdf")
    case_baseline(plain)
    writer = PdfWriter(clone_from=PdfReader(plain))
    writer.encrypt(user_password=user_password, owner_password="synthetic-owner", algorithm="RC4-128")
    writer.write(path)
    plain.unlink()


def case_encrypted_user(path):
    _encrypted(path, "synthetic-user")


def case_encrypted_empty_user(path):
    # Owner-password-only PDF: opens in every viewer without a password.
    _encrypted(path, "")


def case_image_and_text(path):
    objects = text_page_objects(b"q 100 0 0 100 20 20 cm /Im1 Do Q BT /F1 12 Tf 20 250 Td (Caption) Tj ET")
    objects[3] = (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Resources << /Font << /F1 4 0 R >> "
                  b"/XObject << /Im1 6 0 R >> >> /Contents 5 0 R >>")
    objects[6] = stream(b"\xff\x00\x00", b"/Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceRGB /BitsPerComponent 8 ")
    path.write_bytes(build(objects))


def case_launch_and_uri(path):
    # Active-content markers: OpenAction /Launch and /URI, JavaScript name tree.
    objects = text_page_objects(b"BT /F1 12 Tf 20 200 Td (Active) Tj ET")
    objects[1] = (b"<< /Type /Catalog /Pages 2 0 R /OpenAction << /S /Launch /F (/bin/false) >> "
                  b"/Names << /JavaScript << /Names [(x) << /S /JavaScript /JS (app.alert(1)) >>] >> >> "
                  b"/AA << /WC << /S /URI /URI (http://127.0.0.1:9/) >> >> >>")
    path.write_bytes(build(objects))


CASES = {name[5:]: fn for name, fn in globals().items() if name.startswith("case_")}


def main():
    mode, work, case = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    work.mkdir(parents=True, exist_ok=True)
    path = work / f"{case}.pdf"
    if mode == "make":
        CASES[case](path)
        return
    from ttree.documents import extract_pdf
    start = time.monotonic()
    result = extract_pdf(path)
    elapsed = time.monotonic() - start
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
    preview = result.text[:50].replace("\n", "\\n")
    print(f"case={case} file_bytes={path.stat().st_size} issue={result.issue!r} "
          f"text_chars={len(result.text)} seconds={elapsed:.2f} peak_rss_mib={peak} preview={preview!r}")


if __name__ == "__main__":
    main()
