"""Benign marker regression for the new optional-import surface."""

import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]
caller = root / ".tmp/task006-doc-caller"
caller.mkdir()
marker = caller / "unexpected-import"
(caller / "olefile.py").write_text(
    f"from pathlib import Path\nPath({str(marker)!r}).write_text('marker')\n"
)
result = subprocess.run(
    [
        str(root / ".tmp/matrix-312/bin/ttree"),
        "--json",
        "--strict",
        str(root / ".tmp/orc-fixture-provenance/testWORD.doc"),
    ],
    cwd=caller,
    capture_output=True,
    text=True,
    timeout=20,
    check=True,
    env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": str(caller)},
)
entry = json.loads(result.stdout)["roots"][0]
assert entry["tokens"] == 163 and entry["complete"] and not marker.exists()
report = dict(
    passed=True,
    tokens=163,
    marker_created=False,
    command="installed console; worker -I; caller contains benign olefile.py marker",
)
(root / "review/task-006/evidence/doc-caller.json").write_text(
    json.dumps(report, indent=2) + "\n"
)
print(json.dumps(report))
