"""Amendment 3: ONE import; reuse unchanged amendment-2 enforcement."""

from __future__ import annotations

import ast
import gzip
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import import_diagnostic as prior


def main(root):
    supervisor = prior.Supervisor(root)  # Exclusive directory prevents reuse.
    (root / "ONE-OBSERVATION-STARTED").write_text("No retry authorized.\n")
    original = prior.membership
    samples, errors = [], []
    dropped = 0
    began = time.monotonic()

    def observe(cgroup):
        nonlocal dropped
        members = original(cgroup)
        observed = []
        for member in members[:64]:
            proc = Path("/proc") / str(member["pid"])
            try:
                executable = os.readlink(proc / "exe")
                native = executable == "/usr/lib/libreoffice/program/soffice.bin"
                item = {
                    **member,
                    "executable": executable,
                    "role": "native-reader" if native else "wrapper",
                }
                if native:
                    status = dict(
                        line.split(":", 1)
                        for line in (proc / "status").read_text().splitlines()
                    )
                    item.update(
                        {
                            key: int(status[key].split()[0])
                            for key in ("VmPeak", "VmSize")
                        }
                    )
                    item["units"] = "KiB"
                birth = (proc / "stat").read_text().rsplit(")", 1)[1].split()[19]
                if birth != member["starttime"]:
                    raise RuntimeError("PID identity changed during sample")
                observed.append(item)
            except FileNotFoundError:
                # A process can end between the membership and status reads.
                if len(errors) < 64:
                    errors.append(
                        {"pid": member["pid"], "kind": "ended-before-complete-sample"}
                    )
            except (OSError, ValueError, KeyError) as exc:
                raise RuntimeError(
                    "native sampling failed: " + type(exc).__name__
                ) from None
        if len(samples) < 1002:
            samples.append(
                {"seconds": round(time.monotonic() - began, 6), "members": observed}
            )
        else:
            dropped += 1
        return members

    data = None
    prior.membership = observe
    try:
        raw = (prior.ROOT / ".tmp/orc-fixture-provenance/testWORD.doc").read_bytes()
        supervisor.check(
            "pinned_fixture",
            len(raw) == 32768
            and raw[:8] == prior.OLE
            and hashlib.sha256(raw).hexdigest() == prior.EXPECTED_SHA
            and hashlib.sha1(b"blob 32768\0" + raw).hexdigest() == prior.EXPECTED_BLOB,
        )
        # Reuse the exact existing private profile literal; do not change policy.
        tree = ast.parse(prior.SCRIPT.read_text())
        profiles = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith('<?xml version="1.0"?><oor:items')
        ]
        assert len(profiles) == 1
        data = prior.fresh(root / "import_1024", "data")
        (data / "input.doc").write_bytes(raw)
        (data / "profile/user/registrymodifications.xcu").write_text(profiles[0])
        command = prior.reader(
            data, "/work/input.doc", "txt:Text (encoded):UTF8", word_filter=True
        )
        previous = json.loads(
            gzip.decompress(
                (
                    prior.ROOT
                    / "review/task-003/evidence/amendment-2-native/results.raw.json.gz"
                ).read_bytes()
            )
        )
        old = previous["cases"]["import_1024"]["command"]
        assert [
            str(data) if arg.endswith("/native-import-1/import_1024/data") else arg
            for arg in old
        ] == command
        supervisor.report["unchanged_enforcement_sha256"] = {
            name: hashlib.sha256((prior.SCRIPT.parent / name).read_bytes()).hexdigest()
            for name in ("import_diagnostic.py", "diagnostic.py", "prototype.py")
        }
        result = supervisor.run("import_1024", command, as_mib=1024)
        output = data / "output/input.txt"
        expected = [
            "Sample Word Document Title",
            "This is a sample Microsoft Word Document.",
        ]
        result["expected_text_observed"] = output.exists() and all(
            text in output.read_text(encoding="utf-8-sig") for text in expected
        )
        result["output_bytes"] = output.stat().st_size if output.exists() else None
        supervisor.report["native_import_success"] = (
            result["status"] == "ok" and result["expected_text_observed"]
        )
    except Exception as exc:
        supervisor.report["failure"] = type(exc).__name__ + ": " + str(exc)
    finally:
        prior.membership = original
        if data is not None:
            shutil.rmtree(data)
            supervisor.report["checks"]["private_data_removed"] = not data.exists()
        native = [
            m
            for sample in samples
            for m in sample["members"]
            if m["role"] == "native-reader"
        ]
        supervisor.report["virtual_size_observation"] = {
            "poll_seconds": 0.02,
            "retained_sample_cap": 1002,
            "dropped_samples": dropped,
            "samples": samples,
            "incomplete_process_samples": errors,
            "native_sample_count": len(native),
            "native_max_VmPeak_KiB": max((m["VmPeak"] for m in native), default=None),
            "native_max_VmSize_KiB": max((m["VmSize"] for m in native), default=None),
            "scope": "actual soffice.bin PID plus starttime; wrappers labelled separately; trusted sibling meter excluded",
            "interpretation": "Polling can miss short lifetimes. Low VmPeak does not exclude denied reservation or another cause. One observation only; no unique causal proof.",
        }
        supervisor.report["passed"] = (
            False  # Native acceptance requires Orc adjudication.
        )
        supervisor.save()
    print(
        json.dumps(
            {
                k: v
                for k, v in supervisor.report.items()
                if k not in {"cases", "virtual_size_observation"}
            }
        )
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
