"""TASK-004 independent functional probes against an installed ttree.

Usage: python -I review/task-004/probe.py TTREE_BIN SCRATCH_DIR OUT_JSON [probe ...]
Synthetic, scaled fixtures only. Absolute roots. The scratch dir holds data only.
Run under: timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0

Each probe records only observed outcomes (exit code, root/entry status, timing),
compares against the documented contract, and emits a neutral verdict. No attack
narration: fixtures exercise the tool's own declared bounds on an installed wheel.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

TTREE, SCRATCH, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
SELECTED = set(sys.argv[4:])
MIB = 1024 * 1024
TMP = SCRATCH / ".tmp"
DOCUMENT = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body><w:p><w:r><w:t>alpha beta gamma delta</w:t></w:r></w:p></w:body></w:document>"
)


def fresh(name):
    path = SCRATCH / name
    if path.exists():
        for item in path.rglob("*"):
            try:
                if item.is_dir():
                    item.chmod(0o700)
            except OSError:
                pass
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    return path


def run(*args, prefix=(), cwd=None):
    started = time.monotonic()
    done = subprocess.run(
        [*prefix, TTREE, *args],
        capture_output=True,
        cwd=str(cwd or SCRATCH),
        env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": str(TMP)},
    )
    return done, round(time.monotonic() - started, 3)


def make_docx(path, media_bytes):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", DOCUMENT)
        info = zipfile.ZipInfo("word/media/image1.bin")
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, os.urandom(media_bytes))


def root_status(done):
    try:
        doc = json.loads(done.stdout)
        root = doc["roots"][0]
        return root["status"], root["tokens"], root["bytes"], root["complete"], doc
    except Exception:
        return "<unparsable>", None, None, None, None


def probe_large_document():
    # A document whose on-disk size sits between response_bytes (12 MiB) and
    # input_bytes (64 MiB), with only a few tokens of extractable text.
    d = fresh("large-doc")
    make_docx(d / "over.docx", 13 * MIB)
    make_docx(d / "under.docx", 11 * MIB)
    over, _ = run("--json", str((d / "over.docx").resolve()))
    under, _ = run("--json", str((d / "under.docx").resolve()))
    return {
        "name": "large-document",
        "over_12MiB_status": root_status(over)[0],
        "under_12MiB_status": root_status(under)[0],
        "expected_both": "counted",
        "verdict": "DEFECT"
        if root_status(over)[0] != "counted" and root_status(under)[0] == "counted"
        else "ok",
    }


def probe_worker_overhead():
    d = fresh("many-md")
    n = 40
    for i in range(n):
        (d / f"f{i:03d}.md").write_text("alpha beta gamma delta epsilon\n")
    normal, wall = run("--json", str(d.resolve()))
    status, tokens, _, complete, doc = root_status(normal)
    per_file = round(wall / n, 4)
    tight, _ = run("--json", "--limit-scan-seconds", "1", str(d.resolve()))
    tstatus, _, _, tcomplete, tdoc = root_status(tight)
    counted = timed = 0
    if tdoc:
        for e in tdoc["roots"][0]["entries"]:
            if e["kind"] == "file":
                counted += e["status"] == "counted"
                timed += e["status"] == "timed_out"
    return {
        "name": "worker-overhead",
        "files": n,
        "wall_seconds": wall,
        "per_file_seconds": per_file,
        "normal_root_status": status,
        "normal_complete": complete,
        "deadline_1s_root_status": tstatus,
        "deadline_1s_counted": counted,
        "deadline_1s_timed_out": timed,
        "extrapolated_max_files_120s": int(120 / per_file) if per_file else None,
    }


def probe_line_separator():
    d = fresh("sep-name")
    name = "a b.md"
    (d / name).write_text("alpha beta\n")
    done, _ = run("-L", "1", str(d.resolve()))
    text = done.stdout.decode("utf-8", "surrogateescape")
    forged = len(text.splitlines())
    return {
        "name": "line-separator-escape",
        "u2028_in_output": " " in text,
        "output_physical_lines": text.count("\n") + 1,
        "output_splitlines_count": forged,
        "verdict": "DEFECT" if " " in text else "ok",
    }


def probe_unreadable_dir():
    d = fresh("noperm")
    sub = d / "locked"
    sub.mkdir()
    (sub / "inside.md").write_text("alpha beta gamma\n")
    sub.chmod(0o000)
    try:
        done, _ = run("--json", str(d.resolve()))
        doc = json.loads(done.stdout)
        entry = next(e for e in doc["roots"][0]["entries"] if e["path"].endswith("locked"))
    finally:
        sub.chmod(0o700)
    return {
        "name": "unreadable-dir-aggregation",
        "entry_status": entry["status"],
        "entry_tokens": entry["tokens"],
        "entry_bytes": entry["bytes"],
        "entry_complete": entry["complete"],
        "note": "tokens/bytes are 0 (not null) while complete is false"
        if entry["tokens"] == 0 and entry["complete"] is False
        else "null or complete as expected",
    }


def probe_denied_userns():
    d = fresh("denyns")
    (d / "plain.md").write_text("alpha beta gamma delta\n")
    helper = "echo 0 > /proc/sys/user/max_user_namespaces 2>/dev/null; exec \"$@\""
    prefix = ["unshare", "-U", "--map-root-user", "sh", "-c", helper, "sh"]
    done, _ = run("--json", str((d / "plain.md").resolve()), prefix=prefix)
    status = root_status(done)[0]
    return {
        "name": "denied-userns",
        "returncode": done.returncode,
        "plain_md_status": status,
        "note": "plain text reports limits_unavailable when userns is denied"
        if status == "limits_unavailable"
        else "status=" + str(status),
    }


def probe_nonutf8_json():
    d = fresh("badname")
    raw = os.fsencode(str(d)) + b"/bad\xff.md"
    with open(raw, "wb") as fh:
        fh.write(b"alpha beta\n")
    done, _ = run("--json", str(d.resolve()))
    jq = subprocess.run(
        ["jq", "-e", ".roots[0].entries"],
        input=done.stdout,
        capture_output=True,
        env={"PATH": "/usr/bin"},
    )
    has_b64 = b"path_bytes_base64" in done.stdout
    return {
        "name": "nonutf8-json-path",
        "jq_returncode": jq.returncode,
        "jq_rejected": jq.returncode != 0,
        "path_bytes_base64_present": has_b64,
        "note": "jq (strict) rejects surrogate escape in path; base64 field is the safe key"
        if jq.returncode != 0 and has_b64
        else "jq accepted",
    }


PROBES = {
    "large-document": probe_large_document,
    "worker-overhead": probe_worker_overhead,
    "line-separator": probe_line_separator,
    "unreadable-dir": probe_unreadable_dir,
    "denied-userns": probe_denied_userns,
    "nonutf8-json": probe_nonutf8_json,
}


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    results = []
    for key, fn in PROBES.items():
        if SELECTED and key not in SELECTED:
            continue
        try:
            results.append(fn())
        except Exception as exc:
            results.append({"name": key, "error": repr(exc)})
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=True) + "\n")
    for r in results:
        print(json.dumps(r, ensure_ascii=True))


if __name__ == "__main__":
    main()
