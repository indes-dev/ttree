"""Read-only audit of retained native diagnostic evidence (outcome fields only).

Usage: python -I review/task-004/native_audit.py EVIDENCE_DIR
Prints case outcomes without commands or document content; stderr is summarised
as line counts plus the first line's error class only.
"""

import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
data = json.loads((root / "results.summary.json").read_text())
print("top-level keys:", [k for k in data if k != "cases"])
for key in ("starting_head", "scope", "batch_wall_seconds", "passed", "native_import_success", "native_controls_complete", "failure", "checks", "elapsed_seconds"):
    print(f"{key}: {data.get(key)}")
for name, case in data["cases"].items():
    fields = {k: v for k, v in case.items() if k not in ("command", "scope_command")}
    print(f"case {name}: {json.dumps(fields, sort_keys=True)[:900]}")
    scalars = {k: v for k, v in fields.items() if not isinstance(v, (dict, list))}
    print(f"case {name} scalars: {json.dumps(scalars, sort_keys=True)}")
    peak = fields.get("before_termination", {}).get("memory.peak")
    print(f"case {name} memory.peak: {peak}")
for path in sorted(root.glob("import_*.stderr")):
    lines = path.read_text(errors="replace").splitlines()
    first = next((line for line in lines if line.strip()), "")
    kind = re.sub(r"[^A-Za-z_: ]", "", first)[:80]
    print(f"{path.name}: {len(lines)} lines; first-line class: {kind!r}")
