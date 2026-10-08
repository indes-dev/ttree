"""Capture real installed CLI examples and normal family timing/RSS."""

from __future__ import annotations

import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from test_documents import make_docx, make_pdf  # noqa: E402


def main(python, work):
    work.mkdir(parents=True, exist_ok=False)
    make_docx(
        work / "normal.docx", "<w:p><w:r><w:t>Readable DOCX text</w:t></w:r></w:p>"
    )
    make_pdf(work / "normal.pdf", "Readable PDF text")
    (work / "utf16.txt").write_bytes("Hello, world!".encode("utf-16"))
    (work / "empty.txt").touch()
    (work / "legacy.doc").write_bytes(bytes.fromhex("d0cf11e0a1b11ae1") + b"SYNTHETIC")
    (work / "latin1.txt").write_bytes(b"\xffSYNTHETIC")
    records = []

    def run(name, expected_exit, *arguments):
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.monotonic()
        result = subprocess.run(
            [
                str(python),
                "-m",
                "ttree.cli",
                *arguments,
            ],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=25,
            env={**os.environ, "TMPDIR": str(work)},
        )
        assert result.returncode == expected_exit
        (work / (name + "-stdout.txt")).write_text(result.stdout)
        (work / (name + "-stderr.txt")).write_text(result.stderr)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        usage = {
            "wall_seconds": round(time.monotonic() - started, 4),
            "user_seconds": round(after.ru_utime - before.ru_utime, 6),
            "system_seconds": round(after.ru_stime - before.ru_stime, 6),
            "peak_rss_kib": after.ru_maxrss,
        }
        record = {
            "name": name,
            "arguments": list(arguments),
            "exit": result.returncode,
            "metrics": usage,
            "metrics_scope": "CPU delta per CLI family; cumulative max waited-process RSS, not aggregate memory. Normal is the first child run.",
        }
        if "--json" in arguments and expected_exit != 2:
            assert result.stdout.endswith("\n") and not result.stderr
            document = json.loads(result.stdout)
            record["result"] = document
        records.append(record)
        return record.get("result")

    normal = run(
        "normal",
        0,
        "--json",
        "--strict",
        "normal.docx",
        "normal.pdf",
        "utf16.txt",
        "empty.txt",
    )
    assert [root["tokens"] for root in normal["roots"]] == [4, 3, 4, 0]
    assert normal["total"]["tokens"] == 11 and normal["total"]["complete"]
    incomplete = run(
        "strict-incomplete", 3, "--json", "--strict", "legacy.doc", "latin1.txt"
    )
    assert [root["status"] for root in incomplete["roots"]] == [
        "unsupported",
        "not_utf8",
    ]
    assert all(root["tokens"] is None for root in incomplete["roots"])
    run("json-default-exit", 0, "--json", "legacy.doc")
    mixed = run(
        "mixed-missing", 1, "--json", "--strict", "normal.docx", "legacy.doc", "missing"
    )
    assert mixed["total"]["tokens"] == 4 and not mixed["total"]["complete"]
    assert (
        mixed["roots"][-1]["status"] == "missing"
        and mixed["roots"][-1]["bytes"] is None
    )
    run("usage", 2, "--json", "--limit-wall-seconds", "0", "normal.pdf")
    report = {
        "passed": True,
        "python": str(python),
        "source_revision": "4382916510f91b065e45d6fdfa7b1243b174d75f",
        "examples": records,
    }
    (work / "results.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "passed": True,
                "examples": len(records),
                "normal_metrics": records[0]["metrics"],
            }
        )
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]).absolute(), Path(sys.argv[2]).resolve())
