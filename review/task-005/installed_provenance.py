"""Compare installed ttree files in each matrix env with the pinned wheel bytes.

Usage: python -I review/task-005/installed_provenance.py WHEEL PROJECT_ROOT
Also reports each env's interpreter version, the imported module location
(run with -I from a private cwd) and the console-script launcher target.
"""

import hashlib
import subprocess
import sys
import tempfile
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
probe = "import sys, ttree; print(sys.version.split()[0], ttree.__file__)"
for v in ("310", "311", "312", "314"):
    env = root / ".tmp" / f"matrix-{v}"
    site = next((env / "lib").glob("python3*/site-packages"))
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
    editable = sorted(p.name for p in site.glob("*.pth") if "ttree" in p.read_text())
    with tempfile.TemporaryDirectory() as cwd:
        where = subprocess.run(
            [str(env / "bin/python"), "-I", "-c", probe],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
    launcher = (env / "bin/ttree").read_text().splitlines()[0]
    print(f"matrix-{v}: {len(members) - len(bad)}/{len(members)} equal; "
          f"mismatched={bad}; extra={extra}; editable_pth={editable}")
    print(f"  import: {where.replace(str(root), '<root>')}")
    print(f"  launcher: {launcher.replace(str(root), '<root>')}")
