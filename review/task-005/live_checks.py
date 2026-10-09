"""TASK-005 benign live checks against the installed console script.

Usage: python3 -I review/task-005/live_checks.py TTREE_BIN WORK_DIR OUT_JSON

A. Inert plain-text .doc quarantine and exit precedence (1 > 3 > 0).
B. Real-clock scan deadline: 40 tiny text files in nested directories with
   --limit-scan-seconds 1; unknown values must stay null, never 0.
All inputs are small synthetic text files. No document readers are exercised
beyond the normal text path; no network.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ttree, work, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
if work.exists():
    shutil.rmtree(work)
cwd = work / "cwd"
tmp = work / "tmp"
for d in (cwd, tmp):
    d.mkdir(parents=True)
env = {"PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": str(tmp)}
OUTER = ["timeout", "--kill-after=1", "115", "prlimit", "--as=2147483648",
         "--cpu=60", "--core=0"]


def run(*args):
    started = time.monotonic()
    proc = subprocess.run(OUTER + [ttree, *args], cwd=cwd, env=env,
                          capture_output=True, text=True)
    return proc, round(time.monotonic() - started, 3)


def entries(doc):
    return [
        {k: e.get(k) for k in ("path", "kind", "status", "tokens", "bytes", "complete")}
        for root in doc["roots"] for e in root["entries"]
    ]


result = {}

# A. DOC quarantine
fx = work / "quarantine"
fx.mkdir()
(fx / "a.txt").write_text("Hello, world!")
(fx / "c.md").write_text("Hello, world!")
(fx / "legacy.doc").write_text("inert synthetic plain text")
proc, secs = run("--json", str(fx))
doc = json.loads(proc.stdout)
result["A_json"] = {"exit": proc.returncode, "seconds": secs,
                    "entries": entries(doc), "total": doc["total"]}
codes = {}
for name, args in {
    "non_strict": (str(fx),),
    "strict": ("--strict", str(fx)),
    "strict_complete_file": ("--strict", str(fx / "c.md")),
    "strict_partial_plus_missing": ("--strict", str(fx), str(fx / "missing-root")),
    "non_strict_missing": (str(fx / "missing-root"),),
}.items():
    codes[name] = run(*args)[0].returncode
result["A_exit_codes"] = codes
proc, _ = run(str(fx / "c.md"), str(fx / "missing-root"))
result["A_human_total_line"] = proc.stdout.splitlines()[-1] if proc.stdout else None

# B. live deadline
dl = work / "deadline"
for i in range(4):
    sub = dl / ("d%d" % i)
    sub.mkdir(parents=True)
    for j in range(10):
        (sub / ("f%02d.txt" % j)).write_text("Hello, world!")
proc, secs = run("--json", "--strict", "--limit-scan-seconds", "1", str(dl))
doc = json.loads(proc.stdout)
ents = entries(doc)
statuses = {}
for e in ents:
    statuses[e["status"]] = statuses.get(e["status"], 0) + 1
bad_zero = [e for e in ents if not e["complete"] and e["status"] != "excluded"
            and e["tokens"] == 0]
result["B_deadline"] = {
    "exit": proc.returncode,
    "seconds": secs,
    "stderr_empty": proc.stderr == "",
    "status_counts": statuses,
    "root": {k: doc["roots"][0].get(k) for k in ("status", "tokens", "bytes", "complete")},
    "total": doc["total"],
    "directories": [e for e in ents if e["kind"] == "directory"],
    "incomplete_with_zero_tokens": bad_zero,
    "counted_files": sum(1 for e in ents if e["kind"] == "file" and e["status"] == "counted"),
}
proc, secs = run("--json", "--strict", str(dl))
doc = json.loads(proc.stdout)
result["B_control_full"] = {"exit": proc.returncode, "seconds": secs,
                            "total": doc["total"]}

out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({k: (v.get("exit") if isinstance(v, dict) and "exit" in v else v)
                  for k, v in result.items()}, indent=1))
