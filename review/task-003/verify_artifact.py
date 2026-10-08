"""Bounded artifact regressions and paired disposable loopback controls."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from zipfile import ZipFile

from prototype import ROOT


def command(args, log, *, okay=True, timeout=45, env=None):
    with log.open("w") as stream:
        result = subprocess.run(
            args,
            cwd=ROOT,
            stdout=stream,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env=env,
        )
    if okay and result.returncode:
        raise RuntimeError(log.name + " failed")
    if not okay and not result.returncode:
        raise RuntimeError(log.name + " unexpectedly succeeded")
    return result.returncode


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def network(artifact, work):
    subprocess.run(["/usr/bin/ip", "link", "set", "lo", "up"], check=True, timeout=1)
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    server.settimeout(0.2)
    port = server.getsockname()[1]
    stopped = threading.Event()
    requests = []

    def listen():
        while not stopped.is_set():
            try:
                client, _ = server.accept()
            except socket.timeout:
                continue
            with client:
                requests.append(True)
                client.sendall(b"SYNTHETIC-LOOPBACK-CONTROL")

    thread = threading.Thread(target=listen)
    thread.start()
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1) as connection:
            assert connection.recv(128) == b"SYNTHETIC-LOOPBACK-CONTROL"
        assert len(requests) == 1
        command(
            [
                "/usr/bin/unshare",
                "-Urn",
                sys.executable,
                str(ROOT / "scripts/validate_offline.py"),
                str(artifact),
                "--loopback-port",
                str(port),
            ],
            work / "offline-validation.log",
            timeout=35,
        )
        assert len(requests) == 1
        return {
            "parent_positive_control": True,
            "nested_namespace_denied": True,
            "parent_listener_connections": len(requests),
        }
    finally:
        stopped.set()
        thread.join(1)
        server.close()


def main(work, artifact, packages):
    work.mkdir(parents=True, exist_ok=False)
    report = {
        "starting_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "checks": {},
        "passed": False,
    }
    started = time.monotonic()

    def check(name, value):
        report["checks"][name] = bool(value)
        if not value:
            raise RuntimeError(name)

    try:
        command(
            [
                sys.executable,
                str(ROOT / "scripts/build_tracked.py"),
                str(work / "repeated-build"),
            ],
            work / "repeat-build.log",
        )
        previous = json.loads((packages / "build.json").read_text())
        repeated = json.loads((work / "repeated-build/packages/build.json").read_text())
        check("tracked_wheel_and_sdist_reproducible", previous == repeated)
        command(
            [
                sys.executable,
                str(ROOT / "scripts/build_offline.py"),
                str(
                    work / "repeated-build/packages/indes_ttree-0.2.0-py3-none-any.whl"
                ),
                str(work / "repeated-artifact"),
            ],
            work / "repeat-artifact.log",
        )
        check(
            "whole_artifact_reproducible",
            sha(artifact / "SHA256SUMS") == sha(work / "repeated-artifact/SHA256SUMS"),
        )
        report["artifacts"] = previous
        report["artifact_sha256sums_digest"] = sha(artifact / "SHA256SUMS")
        report["manifest"] = json.loads((artifact / "manifest.json").read_text())
        sentinels = [
            ROOT / "task003-untracked-private.txt",
            ROOT / "src/ttree/task003-private-contract.txt",
            ROOT / "tests/task003-secret.key",
            ROOT / "LICENSE-task003-untracked",
        ]
        check("sentinel_paths_fresh", all(not path.exists() for path in sentinels))
        try:
            for path in sentinels:
                path.write_text("SYNTHETIC-NOT-PRIVATE-TASK003")
            command(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--no-isolation",
                    "--outdir",
                    str(work / "dirty-build"),
                ],
                work / "dirty-build.log",
            )
            import tarfile

            with tarfile.open(work / "dirty-build/indes_ttree-0.2.0.tar.gz") as archive:
                sdist = archive.getnames()
            with ZipFile(
                work / "dirty-build/indes_ttree-0.2.0-py3-none-any.whl"
            ) as archive:
                wheel = archive.namelist()
            check(
                "root_src_tests_license_sentinels_excluded",
                all(
                    not any(path.name in name for name in [*sdist, *wheel])
                    for path in sentinels
                ),
            )
            check(
                "required_code_tests_build_inputs_licenses_in_sdist",
                all(
                    any(name.endswith("/" + required) for name in sdist)
                    for required in [
                        "hatch_build.py",
                        "src/ttree/worker.py",
                        "src/ttree/data/o200k_base.tiktoken",
                        "src/ttree/data/TIKTOKEN_LICENSE",
                        "LICENSE",
                        "tests/test_security.py",
                        "scripts/build_offline.py",
                        "locks/runtime-linux-cp312-x86_64.txt",
                    ]
                ),
            )
            check(
                "fixtures_reviews_and_test_assets_not_in_wheel",
                not any(
                    name.startswith(("tests/", "review/", "docs/"))
                    or name.endswith(".doc")
                    for name in wheel
                ),
            )
            report["distribution_inventory"] = {"sdist": sdist, "wheel": wheel}
        finally:
            for path in sentinels:
                if path.exists():
                    assert path.read_text() == "SYNTHETIC-NOT-PRIVATE-TASK003"
                    path.unlink()
        implicit = ROOT / ".hgignore"
        check("implicit_path_fresh", not implicit.exists())
        try:
            implicit.write_text("SYNTHETIC-NOT-PRIVATE-TASK003")
            command(
                [
                    sys.executable,
                    "-m",
                    "build",
                    "--no-isolation",
                    "--outdir",
                    str(work / "implicit-build"),
                ],
                work / "implicit-build.log",
                okay=False,
            )
            check(
                "unexpected_implicit_build_input_fails_closed",
                "distribution file list differs from explicit allowlist"
                in (work / "implicit-build.log").read_text(),
            )
        finally:
            if implicit.exists():
                assert implicit.read_text() == "SYNTHETIC-NOT-PRIVATE-TASK003"
                implicit.unlink()
        missing = work / "missing-hash.txt"
        lines = (ROOT / "locks/runtime-linux-cp312-x86_64.txt").read_text().splitlines()
        index = next(i for i, line in enumerate(lines) if "--hash=" in line)
        lines[index] = lines[index].split(" --hash=")[0]
        missing.write_text("\n".join(lines) + "\n")
        command(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--require-hashes",
                "--only-binary=:all:",
                "--no-index",
                "--find-links",
                str(artifact / "wheels"),
                "-r",
                str(missing),
                "--dest",
                str(work / "missing-hash-output"),
            ],
            work / "missing-hash.log",
            okay=False,
        )
        check(
            "missing_hash_rejected",
            "Hashes are required" in (work / "missing-hash.log").read_text(),
        )
        tampered = work / "tampered-wheels"
        shutil.copytree(artifact / "wheels", tampered)
        path = next(tampered.glob("pypdf-*.whl"))
        with ZipFile(path) as archive:
            contents = {
                info.filename: archive.read(info.filename)
                for info in archive.infolist()
            }
        metadata = next(name for name in contents if name.endswith("/METADATA"))
        contents[metadata] += b"\nTask003-Synthetic: byte-integrity-control\n"
        with ZipFile(path, "w") as archive:
            for name, data in contents.items():
                archive.writestr(name, data)
        check(
            "actual_wheel_bytes_tampered",
            sha(path) != sha(artifact / "wheels" / path.name),
        )
        command(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--require-hashes",
                "--only-binary=:all:",
                "--no-index",
                "--find-links",
                str(tampered),
                "-r",
                str(artifact / "install-lock.txt"),
                "--dest",
                str(work / "tampered-output"),
            ],
            work / "tamper.log",
            okay=False,
        )
        check(
            "tampered_wheel_hash_rejected",
            "DO NOT MATCH THE HASHES" in (work / "tamper.log").read_text(),
        )
        args = [
            "/usr/bin/unshare",
            "-Urnpf",
            "--mount-proc",
            sys.executable,
            str(Path(__file__).resolve()),
            "network",
            str(artifact),
            str(work),
        ]
        command(
            args,
            work / "network-outer.log",
            timeout=40,
            env={**os.environ, "TMPDIR": str(ROOT / ".tmp")},
        )
        report["network"] = json.loads((work / "network-proof.json").read_text())
        check(
            "live_positive_and_denial",
            all(
                report["network"][name]
                for name in ("parent_positive_control", "nested_namespace_denied")
            ),
        )
        report["passed"] = True
    except Exception as exc:
        report["failure"] = type(exc).__name__ + ": " + str(exc)
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 4)
        (work / "results.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n"
        )
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "checks": report["checks"],
                "failure": report.get("failure"),
                "seconds": report["elapsed_seconds"],
            }
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    if sys.argv[1] == "network":
        result = network(Path(sys.argv[2]), Path(sys.argv[3]))
        (Path(sys.argv[3]) / "network-proof.json").write_text(json.dumps(result) + "\n")
    else:
        raise SystemExit(main(*(Path(value).resolve() for value in sys.argv[1:4])))
