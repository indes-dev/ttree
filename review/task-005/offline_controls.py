"""Offline install controls for the hash-locked artifact, run inside a network namespace.

Usage (from the worktree):
  unshare -rn timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0 \
    PYTHON -I review/task-005/offline_controls.py ARTIFACT_DIR WORK_DIR OUT_JSON
PYTHON is a CPython 3.12 used only to create fresh venvs. No traffic leaves the namespace.
"""

import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

artifact, work, out = (Path(v).resolve() for v in sys.argv[1:4])
shutil.rmtree(work, ignore_errors=True)
work.mkdir(parents=True)
result = {}

# Network pair: no route to a documentation-range address; loopback works once up.
try:
    socket.create_connection(("192.0.2.1", 9), timeout=2).close()
    result["external_denied"] = False
except OSError as exc:
    result["external_denied"] = True
    result["external_error"] = type(exc).__name__
subprocess.run(["ip", "link", "set", "lo", "up"], check=False)
server = socket.socket()
server.bind(("127.0.0.1", 0))
server.listen(1)
client = socket.create_connection(server.getsockname(), timeout=2)
result["loopback_ok"] = True
client.close()
server.close()


def install(name, wheels, lock):
    venv = work / name
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    done = subprocess.run(
        [str(venv / "bin/python"), "-m", "pip", "install", "--no-index",
         "--disable-pip-version-check", "--find-links", str(wheels),
         "--require-hashes", "-r", str(lock)],
        capture_output=True, text=True,
    )
    (work / f"{name}.log").write_text(done.stdout + done.stderr)
    return venv, done


venv, done = install("positive", artifact / "wheels", artifact / "install-lock.txt")
result["positive_rc"] = done.returncode
sample = work / "sample.md"
sample.write_text("alpha beta gamma delta\n")
smoke = subprocess.run([str(venv / "bin/ttree"), "--json", str(sample)],
                       capture_output=True, text=True, cwd=str(work))
root = json.loads(smoke.stdout)["roots"][0]
result["positive_smoke"] = {"status": root["status"], "tokens": root["tokens"]}

tampered = work / "tampered-wheels"
shutil.copytree(artifact / "wheels", tampered)
target = next(tampered.glob("pypdf-*.whl"))
data = bytearray(target.read_bytes())
data[-1] ^= 0xFF
target.write_bytes(bytes(data))
_, done = install("tampered", tampered, artifact / "install-lock.txt")
result["tampered_rc"] = done.returncode
result["tampered_hash_error"] = "hash" in (done.stdout + done.stderr).lower()

lock = work / "missing-hash-lock.txt"
lines = (artifact / "install-lock.txt").read_text().splitlines()
lock.write_text("\n".join(
    line.split(" --hash")[0] if line.startswith("pypdf==") else line for line in lines
) + "\n")
_, done = install("missing-hash", artifact / "wheels", lock)
result["missing_hash_rc"] = done.returncode
result["missing_hash_error"] = "hash" in (done.stdout + done.stderr).lower()

result["passed"] = (
    result["external_denied"] and result["loopback_ok"] and result["positive_rc"] == 0
    and result["positive_smoke"]["status"] == "counted"
    and result["tampered_rc"] != 0 and result["tampered_hash_error"]
    and result["missing_hash_rc"] != 0 and result["missing_hash_error"]
)
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
