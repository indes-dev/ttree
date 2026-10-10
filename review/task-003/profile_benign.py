"""Bounded installed-wheel small-file profile; no architecture changes."""

from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path


def main(python, work):
    work.mkdir(parents=True, exist_ok=False)
    records = []

    def measure(name, args):
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        start = time.monotonic()
        process = subprocess.run(
            [str(python), "-I", *args],
            cwd=work,
            env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": str(work)},
            capture_output=True,
            text=True,
            timeout=40,
            check=True,
        )
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        records.append(
            {
                "name": name,
                "wall_seconds": time.monotonic() - start,
                "cpu_seconds": after.ru_utime
                + after.ru_stime
                - before.ru_utime
                - before.ru_stime,
                "cumulative_waited_process_max_rss_kib": after.ru_maxrss,
            }
        )
        return process.stdout

    # First child is the representative whole CLI family, giving its RSS scope.
    scanned = work / "files"
    scanned.mkdir()
    for index in range(40):
        (scanned / f"{index:03}.txt").write_text("Hello, world!")
    value = json.loads(
        measure(
            "40-small-files", ["-m", "ttree.cli", "--json", "--strict", str(scanned)]
        )
    )
    assert value["total"] == {"tokens": 160, "bytes": 520, "complete": True}
    for repeat in range(3):
        measure(f"interpreter-start-{repeat}", ["-c", "pass"])
        measure(f"worker-imports-{repeat}", ["-c", "import ttree.worker"])
        measure(
            f"tokenizer-load-{repeat}",
            [
                "-c",
                "from ttree.cli import load_tokenizer; assert len(load_tokenizer().encode(b'Hello, world!'))==4",
            ],
        )
    first = records[0]
    report = {
        "batch_size": 40,
        "passed": True,
        "python": str(python),
        "records": records,
        "metrics_scope": "CPU delta for waited CLI family and descendants; RSS maximum of waited processes, not aggregate memory. First record has no prior child RSS contamination.",
        "projection_only_entries_per_120s": 120 * 40 / first["wall_seconds"],
        "projection_limits": "Linear projection for identical tiny files on this host only. Not a fixed entry cap; no guarantee for other formats, load, directory shapes or deadlines.",
        "decision": "Preserve fresh per-file isolated workers and caps. No proven local optimization implemented. Persistent pools/batching require Orc adjudication; caller can select bounded subtrees as a measured workflow alternative, without changing the 120s ceiling.",
    }
    (work / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main(Path(sys.argv[1]).absolute(), Path(sys.argv[2]).resolve())
