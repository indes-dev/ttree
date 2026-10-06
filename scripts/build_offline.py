"""Collect binary wheels and checksums for an offline installation.

Run with a Python interpreter that has pip. Build the ttree wheel first.
The artifact targets this interpreter's Python, OS and architecture.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output", type=Path, help="new output directory")
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error("provide a built ttree wheel")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    wheels = output / "wheels"
    wheels.mkdir()
    subprocess.run(
        [sys.executable, "-m", "pip", "download", "--only-binary=:all:",
         "--dest", str(wheels), str(wheel)], check=True,
    )
    with ZipFile(wheel) as archive:
        metadata = archive.read(next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))).decode()
    version = next(line.removeprefix("Version: ") for line in metadata.splitlines() if line.startswith("Version: "))
    (output / "manifest.json").write_text(json.dumps({
        "project": "indes-ttree", "version": version,
        "python": platform.python_version(), "system": platform.system(),
        "architecture": platform.machine(),
        "wheels": sorted(path.name for path in wheels.glob("*.whl")),
        "optional_doc_reader": "LibreOffice (not included)",
    }, indent=2) + "\n")
    (output / "INSTALL.md").write_text(
        f"# Offline ttree {version}\n\n"
        "Use an existing compatible Python and uv or pip. See manifest.json for the target platform.\n"
        "Verify SHA256SUMS against the checksum supplied with this artifact. Then verify its files:\n\n"
        "```sh\nsha256sum -c SHA256SUMS\n"
        f"uv tool install --offline --no-index --no-python-downloads --find-links wheels indes-ttree=={version}\n"
        "ttree --help\n```\n\n"
        "Alternatively, use an existing Python environment with pip:\n\n"
        f"```sh\npython -m pip install --no-index --find-links wheels indes-ttree=={version}\n```\n\n"
        "The verified vocabulary and DOCX/PDF readers are included. Runtime does not download files.\n"
        "Legacy DOC additionally needs a locally installed LibreOffice. No OCR runs.\n"
        "Package license notices are included in the wheels.\n"
    )
    paths = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "SHA256SUMS").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output).as_posix()}\n"
        for path in paths
    ))
    print("Offline artifact:", output)
    print("SHA256SUMS SHA-256:", hashlib.sha256((output / "SHA256SUMS").read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
