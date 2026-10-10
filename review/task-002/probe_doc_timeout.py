"""TASK-002 DOC timeout and process-cleanup probes with real processes (no mocks).

Usage: python probe_doc_timeout.py WORKDIR
1. Real LibreOffice with the timeout lowered to 0.2 s, so the reader is killed
   during start-up/conversion. Checks survivors and temporary-directory cleanup.
2. A fake `libreoffice` on PATH that starts a child in its process group and a
   grandchild in a new session (setsid). Shows what os.killpg() can and cannot reach.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import ttree.documents as documents


def processes_matching(token: str) -> list[str]:
    found = []
    for proc in Path("/proc").iterdir():
        if proc.name.isdigit() and int(proc.name) != os.getpid():
            try:
                cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            except OSError:
                continue
            if token in cmdline:
                found.append(f"{proc.name}:{cmdline.strip()[:60]}")
    return found


def main():
    work = Path(sys.argv[1]).resolve()
    private_tmp = work / "tmpdir"
    private_tmp.mkdir()
    os.environ["TMPDIR"] = str(private_tmp)
    tempfile.tempdir = None

    # 1. Real reader, interrupted.
    reader = shutil.which("libreoffice") or shutil.which("soffice")
    source = work / "real.txt"
    source.write_text("Synthetic text for a legacy DOC.\n")
    subprocess.run([reader, f"-env:UserInstallation={(work / 'gen-profile').as_uri()}", "--headless",
                    "--convert-to", "doc:MS Word 97", "--outdir", str(work), str(source)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    documents.DOC_TIMEOUT_SECONDS = 0.2
    result = documents.extract_doc(work / "real.doc")
    time.sleep(2)
    print(f"real-reader timeout: issue={result.issue!r} survivors={processes_matching('ttree-doc-')} "
          f"tmp_leftovers={sorted(str(p.relative_to(private_tmp)) + ('' if p.is_dir() else ' (' + str(p.stat().st_size) + ' B)') for p in private_tmp.rglob('*'))}")

    # 2. Fake reader with an escaping grandchild.
    fake_bin = work / "fakebin"
    fake_bin.mkdir()
    fake = fake_bin / "libreoffice"
    fake.write_text("#!/bin/sh\nsleep 311 &\nsetsid sleep 312 &\nexec sleep 313\n")
    fake.chmod(0o755)
    os.environ["PATH"] = f"{fake_bin}:{os.environ['PATH']}"
    documents.DOC_TIMEOUT_SECONDS = 2
    result = documents.extract_doc(work / "real.doc")
    time.sleep(1)
    survivors = processes_matching("sleep 31")
    print(f"fake-reader timeout: issue={result.issue!r} survivors={survivors} "
          f"tmp_leftovers={sorted(str(p.relative_to(private_tmp)) + ('' if p.is_dir() else ' (' + str(p.stat().st_size) + ' B)') for p in private_tmp.rglob('*'))}")
    for item in survivors:
        os.kill(int(item.split(":")[0]), 9)


if __name__ == "__main__":
    main()
