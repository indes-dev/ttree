"""Benign installed-artifact validation. Invoke through run_validation.sh.

The wrapper provides the disposable outer PID/network namespace required by the
paired loopback control. Never call the listener helper in the host namespace.
No hostile document generation.
"""

from __future__ import annotations

import hashlib
import json
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "review/task-006/evidence"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    packages = ROOT / ".tmp/task006-final-build/packages"
    repeat = ROOT / ".tmp/task006-final-repeat/packages"
    wheel = packages / "indes_ttree-0.2.0-py3-none-any.whl"
    build = json.loads((packages / "build.json").read_text())
    reproduction = {}
    for path in packages.iterdir():
        reproduction[path.name] = sha(path)
        assert sha(path) == sha(repeat / path.name)
    (EVIDENCE / "build.json").write_bytes((packages / "build.json").read_bytes())
    artifact = ROOT / ".tmp/task006-final-offline"
    for name in ("manifest.json", "SHA256SUMS", "install-lock.txt"):
        (EVIDENCE / ("offline-" + name)).write_bytes((artifact / name).read_bytes())
    fixture = ROOT / ".tmp/orc-fixture-provenance/testWORD.doc"
    report = {
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "production_revision": build["source_revision"],
        "checks": {},
        "reproduction": reproduction,
        "public_doc": {"sha256": sha(fixture), "bytes": fixture.stat().st_size},
        "installed": {},
    }
    with ZipFile(wheel) as archive:
        modules = {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("ttree/")
        }
    for minor in ("310", "311", "312", "314"):
        python = ROOT / f".tmp/matrix-{minor}/bin/python"
        provenance = subprocess.check_output(
            [
                str(python),
                "-I",
                "-c",
                "import hashlib,json,sys,ttree;from pathlib import Path;from importlib.metadata import version;"
                "p=Path(ttree.__file__).parent;"
                'print(json.dumps(dict(python=sys.version.split()[0],olefile=version("olefile"),'
                'hashes={"ttree/"+str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() '
                'for f in p.rglob("*") if f.is_file() and "__pycache__" not in str(f)})))',
            ],
            text=True,
        )
        installed = json.loads(provenance)
        assert installed["hashes"] == modules
        result = subprocess.run(
            [str(python.parent / "ttree"), "--json", "--strict", str(fixture)],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
            cwd=ROOT / ".tmp",
            env={"PATH": "/usr/bin", "LANG": "C.UTF-8"},
        )
        entry = json.loads(result.stdout)["roots"][0]
        assert (
            entry["complete"]
            and entry["status"] == "counted"
            and entry["tokens"] == 163
        )
        installed["public_doc"] = {
            k: entry[k] for k in ("bytes", "tokens", "complete", "status")
        }
        report["installed"][minor] = installed
    report["checks"]["reproducible_build"] = True
    report["checks"]["four_installed_provenances_and_public_doc"] = True
    sys.path.insert(0, str(ROOT / "review/task-003"))
    from verify_artifact import network

    offline_work = ROOT / ".tmp/task006-offline-proof"
    offline_work.mkdir(exist_ok=True)
    report["offline"] = network(artifact, offline_work)
    (EVIDENCE / "offline-validation.log").write_bytes(
        (offline_work / "offline-validation.log").read_bytes()
    )
    report["checks"]["offline_network_denial_and_hash_install"] = True
    # Profile only the final installed wheel; this file is itself the provenance.
    work = ROOT / ".tmp/task006-final-profile"
    work.mkdir()
    for index in range(40):
        (work / f"{index:03}.txt").write_text(f"Readable file number {index}.\n")
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    result = subprocess.run(
        [str(ROOT / ".tmp/matrix-312/bin/ttree"), "--json", "--strict", str(work)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    elapsed = time.monotonic() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    value = json.loads(result.stdout)
    assert value["total"]["complete"] and len(value["roots"][0]["entries"]) == 41
    report["profile"] = dict(
        files=40,
        wall_seconds=elapsed,
        cpu_seconds=after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
        tokens=value["total"]["tokens"],
        wheel_sha256=sha(wheel),
        scope="Waited CLI family CPU; 40 distinct benign files; no aggregate RSS claim.",
    )
    report["checks"]["final_wheel_profile"] = True
    for name in ("olefile", "pypdf"):
        path = ROOT / f".tmp/task006-{name}-advisories.json"
        advisories = json.loads(path.read_text())
        assert not advisories, name
        (EVIDENCE / f"{name}-advisories.json").write_bytes(path.read_bytes())
    report["checks"]["dated_direct_reader_advisory_queries_empty"] = True
    report["passed"] = True
    (EVIDENCE / "completion.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {"passed": True, "checks": report["checks"], "profile": report["profile"]}
        )
    )


if __name__ == "__main__":
    main()
