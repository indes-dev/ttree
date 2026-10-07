"""Build only tracked input at an exact revision, using installed locked tools."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
from importlib.metadata import version
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="fresh output directory")
    parser.add_argument("--revision", default="HEAD")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", args.revision + "^{commit}"],
        cwd=root,
        text=True,
    ).strip()
    epoch = subprocess.check_output(
        ["git", "show", "-s", "--format=%ct", revision], cwd=root, text=True
    ).strip()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source"
    source.mkdir()
    packages = output / "packages"
    packages.mkdir()
    archive = subprocess.check_output(
        ["git", "archive", "--format=tar", revision], cwd=root
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        members = tar.getmembers()
        for member in members:
            if (
                member.name.startswith("/")
                or ".." in Path(member.name).parts
                or not (member.isfile() or member.isdir())
            ):
                raise RuntimeError("tracked export contains unsupported paths or links")
        tar.extractall(source, members=members)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            "--outdir",
            str(packages),
            str(source),
        ],
        check=True,
        env={**os.environ, "SOURCE_DATE_EPOCH": epoch},
    )
    metadata = {
        "source_revision": revision,
        "source_date_epoch": int(epoch),
        "build_tools": {
            name: version(name)
            for name in (
                "build",
                "hatchling",
                "packaging",
                "pathspec",
                "pluggy",
                "tomlkit",
                "pyproject-hooks",
                "trove-classifiers",
            )
        },
        "files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(packages.iterdir())
            if p.is_file()
        },
    }
    (packages / "build.json").write_text(
        json.dumps(metadata, sort_keys=True, indent=2) + "\n"
    )
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    main()
