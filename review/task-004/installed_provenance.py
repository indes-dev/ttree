"""Compare installed ttree files in each matrix env with the pinned wheel bytes.

Usage: python -I review/task-004/installed_provenance.py WHEEL PROJECT_ROOT
"""

import hashlib
import sys
import zipfile
from pathlib import Path

wheel, root = Path(sys.argv[1]), Path(sys.argv[2])
print("wheel", hashlib.sha256(wheel.read_bytes()).hexdigest())
with zipfile.ZipFile(wheel) as zf:
    members = {
        n: hashlib.sha256(zf.read(n)).hexdigest()
        for n in zf.namelist()
        if n.startswith("ttree/") and not n.endswith("/")
    }
for v in ("310", "311", "312", "314"):
    site = next((root / ".tmp" / f"matrix-{v}" / "lib").glob("python3*/site-packages"))
    bad = [
        n
        for n, digest in members.items()
        if not (site / n).is_file()
        or hashlib.sha256((site / n).read_bytes()).hexdigest() != digest
    ]
    extra = sorted(
        str(p.relative_to(site))
        for p in (site / "ttree").rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and str(p.relative_to(site)) not in members
    )
    print(f"matrix-{v}: {len(members) - len(bad)}/{len(members)} equal; mismatched={bad}; extra={extra}")
