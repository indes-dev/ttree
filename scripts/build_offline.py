"""Prepare a hash-enforced CPython 3.12/Linux x86_64 offline artifact.

The supplied application wheel must come from build_tracked.py. No release is
published; hashes establish byte integrity, not publisher identity.
"""

from __future__ import annotations

import argparse
import email
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wheel_metadata(path):
    with ZipFile(path) as archive:
        return email.message_from_bytes(
            archive.read(
                next(
                    name
                    for name in archive.namelist()
                    if name.endswith(".dist-info/METADATA")
                )
            )
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("output", type=Path, help="fresh output directory")
    parser.add_argument(
        "--lock",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "locks/runtime-linux-cp312-x86_64.txt",
    )
    args = parser.parse_args()
    if (
        sys.implementation.name != "cpython"
        or sys.version_info[:2] != (3, 12)
        or platform.system() != "Linux"
        or platform.machine() != "x86_64"
    ):
        parser.error(
            "this committed artifact lock targets CPython 3.12/Linux x86_64 only"
        )
    wheel = args.wheel.resolve()
    lock = args.lock.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        parser.error("provide a tracked-build application wheel")
    buildfile = wheel.parent / "build.json"
    build = json.loads(buildfile.read_text())
    if build.get("files", {}).get(wheel.name) != digest(wheel):
        parser.error("wheel differs from tracked-build provenance")
    application = wheel_metadata(wheel)
    if application["Name"] != "indes-ttree":
        parser.error("unexpected application wheel")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    wheels = output / "wheels"
    wheels.mkdir()
    shutil.copyfile(wheel, wheels / wheel.name)
    shutil.copyfile(lock, output / "dependency-lock.txt")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--require-hashes",
            "--only-binary=:all:",
            "--dest",
            str(wheels),
            "-r",
            str(output / "dependency-lock.txt"),
        ],
        check=True,
    )
    install = output / "install-lock.txt"
    install.write_text(
        f"indes-ttree=={application['Version']} --hash=sha256:{digest(wheel)}\n"
        + lock.read_text()
    )
    versions = {}
    for path in sorted(wheels.glob("*.whl")):
        metadata = wheel_metadata(path)
        versions[metadata["Name"]] = metadata["Version"]
    shutil.copyfile(buildfile, output / "tracked-build.json")
    manifest = {
        "project": "indes-ttree",
        "version": application["Version"],
        "source_revision": build["source_revision"],
        "source_date_epoch": build["source_date_epoch"],
        "target": {
            "implementation": "cpython",
            "python": "3.12",
            "system": "Linux",
            "architecture": "x86_64",
        },
        "build_host": {
            "python": platform.python_version(),
            "libc": platform.libc_ver(),
        },
        "build_tools": build["build_tools"],
        "dependency_lock_sha256": digest(lock),
        "install_lock_sha256": digest(install),
        "versions": versions,
        "wheels": sorted(p.name for p in wheels.glob("*.whl")),
        "doc_reader": "static Word 97-2003 text via included olefile; no native program",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    (output / "INSTALL.md").write_text("""# Offline candidate installation

Use CPython 3.12 on Linux x86_64 and an existing pip. Verify the SHA256SUMS digest
received through a separate trusted channel, then the files. Checksums alone do
not prove origin. This task prepares the digest; it does not publish a release.

```sh
sha256sum -c SHA256SUMS
python -m pip install --no-index --find-links wheels --require-hashes -r install-lock.txt
ttree --json --strict docs
```

The artifact includes the entire declared dependency closure and bundled verified
vocabulary and the static DOC reader. Runtime makes no downloads. DOC parsing never
launches a native program; encrypted or unsupported variants remain incomplete.
Python/installer/native tools are not included. License notices remain in wheels.
""")
    paths = sorted(path for path in output.rglob("*") if path.is_file())
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{digest(path)}  {path.relative_to(output).as_posix()}\n" for path in paths
        )
    )
    print(
        json.dumps(
            {
                "artifact": str(output),
                "sha256sums_sha256": digest(output / "SHA256SUMS"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
