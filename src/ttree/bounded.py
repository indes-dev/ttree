"""Bounded IPC supervisor; wait for the entire PID namespace before returning."""

from __future__ import annotations

import json
import os
import selectors
import stat
import subprocess
import sys
import tempfile
import time

STATUSES = {
    "counted",
    "empty",
    "no_text",
    "partial",
    "failed",
    "too_large",
    "encrypted",
    "limits_unavailable",
    "not_utf8",
    "reader_unavailable",
    "changed",
}


def count_fd(fd, kind, limits, deadline):
    if sys.platform != "linux" or not hasattr(os, "pidfd_open"):
        return {"status": "limits_unavailable", "tokens": None}
    if time.monotonic() >= deadline:
        return {"status": "timed_out", "tokens": None}
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        return {"status": "unreadable", "tokens": None}
    if info.st_size > limits["input_bytes"]:
        return {"status": "too_large", "tokens": None}
    with tempfile.TemporaryDirectory(prefix="ttree-base-") as private:
        return supervise(fd, kind, limits, deadline, private)


def supervise(fd, kind, limits, deadline, private):
    started = time.monotonic()
    deadline = min(deadline, started + limits["wall_seconds"])
    control_read, control_write = os.pipe()
    namespace_fd = process = None
    status = None
    output = bytearray()
    received = 0
    try:
        command = [
            sys.executable,
            "-m",
            "ttree.worker",
            str(fd),
            kind,
            str(control_write),
            json.dumps(limits, separators=(",", ":")),
            str(os.getpid()),
        ]
        process = subprocess.Popen(
            command,
            pass_fds=(fd, control_write),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": private},
        )
        os.close(control_write)
        control_write = None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            selector.register(control_read, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    status = "timed_out"
                    break
                events = selector.select(min(0.05, remaining))
                for key, _ in events:
                    if key.fd == control_read:
                        identity = os.read(control_read, 32)
                        selector.unregister(control_read)
                        if identity:
                            if not identity.isdigit() or len(identity) > 20:
                                status = "failed"
                                break
                            try:
                                namespace_fd = os.pidfd_open(int(identity))
                            except ProcessLookupError:
                                pass
                            except OSError:
                                status = "limits_unavailable"
                                break
                if status:
                    break
                if not any(key.fd == process.stdout.fileno() for key, _ in events):
                    continue
                chunk = os.read(
                    process.stdout.fileno(),
                    min(65536, limits["response_bytes"] - len(output) + 1),
                )
                received += len(chunk)
                if not chunk:
                    break
                if len(output) + len(chunk) > limits["response_bytes"]:
                    status = "too_large"
                    break
                output.extend(chunk)
        if status:
            process.kill()
        try:
            process.wait(timeout=max(0.001, min(1, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            status = "timed_out"
            process.kill()
            process.wait()
    except (OSError, ValueError):
        status = "limits_unavailable"
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()
        if namespace_fd is not None:
            with selectors.DefaultSelector() as cleanup:
                cleanup.register(namespace_fd, selectors.EVENT_READ)
                if not cleanup.select(2):
                    status = "limits_unavailable"
            os.close(namespace_fd)
        os.close(control_read)
        if control_write is not None:
            os.close(control_write)
    if status:
        return {"status": status, "tokens": None}
    if process is None or process.returncode:
        return {"status": "failed", "tokens": None}
    try:
        value = json.loads(output)
        if not isinstance(value, dict) or value.get("status") not in STATUSES:
            raise ValueError
        tokens = value.get("tokens")
        if tokens is not None and (
            isinstance(tokens, bool)
            or not isinstance(tokens, int)
            or not 0 <= tokens <= 4 * limits["characters"]
        ):
            raise ValueError
        if value["status"] in {"counted", "empty", "no_text"} and tokens is None:
            raise ValueError
        return {"status": value["status"], "tokens": tokens}
    except (ValueError, UnicodeError, RecursionError):
        return {"status": "failed", "tokens": None}
