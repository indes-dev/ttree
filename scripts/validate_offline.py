"""Validate a wheel artifact with an empty installer cache and new tool directory.

Run under `unshare -Urn` on Linux to block network access at the OS level.
Requires uv and an existing compatible Python. Fixtures are synthetic only.
"""

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    # Require evidence of an actual network block, not just installer flags.
    with socket.socket() as connection:
        connection.settimeout(1)
        try:
            connection.connect(("1.1.1.1", 443))
        except OSError:
            pass
        else:
            raise RuntimeError("network is reachable; run under unshare -Urn")
    for line in (artifact / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((artifact / name).read_bytes()).hexdigest() == digest, name
    version = json.loads((artifact / "manifest.json").read_text())["version"]
    with tempfile.TemporaryDirectory(prefix="ttree-offline-") as temp:
        work = Path(temp)
        env = dict(os.environ, UV_TOOL_DIR=str(work / "tools"),
                   UV_TOOL_BIN_DIR=str(work / "bin"), UV_CACHE_DIR=str(work / "cache"),
                   XDG_DATA_HOME=str(work / "data"), UV_PYTHON_DOWNLOADS="never")
        subprocess.run(["uv", "tool", "install", "--offline", "--no-index",
                        "--no-config", "--no-python-downloads", "--python", sys.executable,
                        "--find-links", str(artifact / "wheels"), f"indes-ttree=={version}"],
                       check=True, env=env)
        fixtures = work / "fixtures"
        fixtures.mkdir()
        (fixtures / "text.md").write_text("Hello, world!")
        with ZipFile(fixtures / "text.docx", "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Readable DOCX text</w:t></w:r></w:p></w:body></w:document>')
        python = work / "tools/indes-ttree/bin/python"
        # Generate a text PDF with the freshly installed reader itself.
        subprocess.run([str(python), "-c", '''
from pathlib import Path
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
import sys
writer = PdfWriter()
page = writer.add_blank_page(width=300, height=300)
font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
stream = DecodedStreamObject()
stream.set_data(b'BT /F1 12 Tf 20 200 Td (Readable PDF text) Tj ET')
page[NameObject('/Contents')] = writer._add_object(stream)
writer.write(Path(sys.argv[1]))
''', str(fixtures / "text.pdf")], check=True, env=env)
        cli = work / "bin/ttree"
        result = subprocess.run([str(cli), "--exact", str(fixtures)], check=True,
                                capture_output=True, text=True, env=env)
        lines = result.stdout.splitlines()
        assert all(any(name in line and "tok" in line for line in lines)
                   for name in ("text.md", "text.docx", "text.pdf")), result.stdout
        assert not re.search(r"\d (?:B|kB|MB)\b", result.stdout)
        assert not (work / "data/ttree").exists()
        installed = subprocess.run([str(python), "-c", "from ttree.cli import tokenizer_path; print(tokenizer_path())"], check=True, capture_output=True, text=True, env=env)
        assert str(work / "tools") in installed.stdout
        print(result.stdout, end="")
        print("PASS: checksums, fresh install, bundled vocabulary, UTF-8/DOCX/PDF count, network blocked.")


if __name__ == "__main__":
    main()
