"""Verify and install the locked artifact with live disposable loopback denial.

Run under unshare -Urn with an existing uv/pip/Python; no external network probe.
The successful positive control runs outside the network namespace; see
review/task-003 artifact evidence for the paired parent listener invocation.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile


def checked(command, **kwargs):
    return subprocess.run(command, check=True, timeout=45, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--loopback-port",
        type=int,
        required=True,
        help="parent disposable positive-control listener port",
    )
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    with socket.socket() as connection:
        connection.settimeout(0.5)
        try:
            connection.connect(("127.0.0.1", args.loopback_port))
        except OSError:
            pass
        else:
            raise RuntimeError(
                "parent loopback is reachable; require disposable unshare -Urn boundary"
            )
    for line in (artifact / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if name.startswith("/") or ".." in Path(name).parts:
            raise RuntimeError("invalid artifact checksum path")
        assert hashlib.sha256((artifact / name).read_bytes()).hexdigest() == expected, (
            name
        )
    manifest = json.loads((artifact / "manifest.json").read_text())
    assert (
        hashlib.sha256((artifact / "dependency-lock.txt").read_bytes()).hexdigest()
        == manifest["dependency_lock_sha256"]
    )
    assert (
        hashlib.sha256((artifact / "install-lock.txt").read_bytes()).hexdigest()
        == manifest["install_lock_sha256"]
    )
    with tempfile.TemporaryDirectory(prefix="ttree-offline-") as temp:
        work = Path(temp)
        environment = work / "venv"
        env = {
            **os.environ,
            "UV_CACHE_DIR": str(work / "empty-cache"),
            "PIP_CACHE_DIR": str(work / "pip-cache"),
            "PIP_CONFIG_FILE": os.devnull,
            "TMPDIR": str(work),
        }
        checked(
            [
                "uv",
                "venv",
                "--no-python-downloads",
                "--python",
                sys.executable,
                str(environment),
            ],
            env=env,
        )
        python = environment / "bin/python"
        checked(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--offline",
                "--no-index",
                "--no-config",
                "--require-hashes",
                "--find-links",
                str(artifact / "wheels"),
                "-r",
                str(artifact / "install-lock.txt"),
            ],
            env=env,
        )
        fixtures = work / "fixtures"
        fixtures.mkdir()
        (fixtures / "text.md").write_text("Hello, world!")
        with ZipFile(fixtures / "text.docx", "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Readable DOCX text</w:t></w:r></w:p></w:body></w:document>',
            )
        (fixtures / "inactive.doc").write_bytes(
            bytes.fromhex("d0cf11e0a1b11ae1") + b"synthetic"
        )
        cli = environment / "bin/ttree"
        result = subprocess.run(
            [str(cli), "--json", "--strict", str(fixtures)],
            capture_output=True,
            text=True,
            timeout=25,
            env=env,
        )
        assert result.returncode == 3 and not result.stderr, result
        value = json.loads(result.stdout)
        entries = {entry["path"]: entry for entry in value["roots"][0]["entries"]}
        assert (
            value["schema_version"] == 1
            and entries["text.md"]["tokens"] == 4
            and entries["text.docx"]["tokens"] == 4
        )
        assert (
            entries["inactive.doc"]["status"] == "unsupported"
            and entries["inactive.doc"]["tokens"] is None
            and not entries["inactive.doc"]["complete"]
        )
        assert value["total"]["tokens"] == 8 and not value["total"]["complete"]
        mixed = subprocess.run(
            [str(cli), "--json", "--strict", str(fixtures), str(work / "missing")],
            capture_output=True,
            text=True,
            timeout=25,
            env=env,
        )
        assert mixed.returncode == 1
        roots = json.loads(mixed.stdout)["roots"]
        assert len(roots) == 2 and roots[1]["status"] == "missing"
        located = checked(
            [str(python), "-c", "import ttree;print(ttree.__file__)"],
            capture_output=True,
            text=True,
            env=env,
        ).stdout.strip()
        assert str(environment) in located
        print(
            json.dumps(
                {
                    "passed": True,
                    "target": manifest["target"],
                    "installed_module": located,
                    "positive_control_port": args.loopback_port,
                    "network_denied": True,
                    "json_strict_exit": result.returncode,
                    "mixed_root_exit": mixed.returncode,
                    "versions": manifest["versions"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
