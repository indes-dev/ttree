"""TASK-005 read-only audit of retained 6d47c42 native observation and N-3 profile.

Usage: python3 -I review/task-005/native_audit.py REPO_ROOT
Prints outcome fields only (scalars, key names, sample counts), never commands,
document content or raw stderr text; stderr is summarised as line count plus
the first line's error class.
"""

import gzip
import json
import re
import sys
from pathlib import Path

repo = Path(sys.argv[1])
native = repo / "review/task-003/evidence/amendment-3-native"
base = repo / "review/task-003/evidence/amendment-3-base"
SKIP = {"command", "scope_command", "argv", "cmd"}


def walk(value, prefix="", depth=0):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in SKIP:
                print(f"{prefix}{key}: <omitted>")
            elif isinstance(item, (dict, list)) and depth < 3:
                size = len(item)
                print(f"{prefix}{key}: {type(item).__name__}[{size}]")
                if isinstance(item, dict) or size <= 6:
                    walk(item, prefix + "  ", depth + 1)
            else:
                text = json.dumps(item)
                print(f"{prefix}{key}: {text[:160]}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, (dict, list)):
                print(f"{prefix}[{index}]")
                walk(item, prefix + "  ", depth + 1)
            else:
                print(f"{prefix}[{index}]: {json.dumps(item)[:160]}")


print("== native results.summary.json")
walk(json.loads((native / "results.summary.json").read_text()))
raw = json.loads(gzip.decompress((native / "results.raw.json.gz").read_bytes()))
print("== native results.raw.json.gz structure")
if isinstance(raw, dict):
    for key, item in raw.items():
        size = len(item) if isinstance(item, (dict, list)) else None
        print(f"{key}: {type(item).__name__}" + (f"[{size}]" if size is not None else ""))
lines = (native / "stderr.txt").read_text(errors="replace").splitlines()
first = next((line for line in lines if line.strip()), "")
print(f"stderr.txt: {len(lines)} lines; first-line class: "
      f"{re.sub(r'[^A-Za-z_: ]', '', first)[:80]!r}")
print("== base profile.json (N-3)")
walk(json.loads((base / "profile.json").read_text()))
