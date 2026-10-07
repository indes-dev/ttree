"""Private bounded base worker; no native adapter or external commands."""

from __future__ import annotations

import ctypes
import json
import os
import resource
import selectors
import signal
import sys
import tempfile
from pathlib import Path

from ttree.documents import Stop, docx, pdf
from ttree.limits import CAPS, validated


def contain(control_fd):
    """Kill namespace descendants even if they fork/setsid/reparent.

    Bootstrap waits for namespace PID 1. PID 1's parent-death signal kills the
    namespace on supervisor termination; check parent identity after prctl to
    close the installation race. Kernel PID namespace teardown kills all members.
    """
    if sys.platform != "linux":
        raise Stop("limits_unavailable")
    uid, gid = os.getuid(), os.getgid()
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.unshare(0x10000000) != 0:
        raise Stop("limits_unavailable")
    try:
        Path("/proc/self/setgroups").write_text("deny")
        Path("/proc/self/uid_map").write_text(f"0 {uid} 1")
        Path("/proc/self/gid_map").write_text(f"0 {gid} 1")
    except OSError:
        raise Stop("limits_unavailable") from None
    if libc.unshare(0x20000000) != 0:
        raise Stop("limits_unavailable")
    child = os.fork()
    if child:
        os.write(control_fd, str(child).encode("ascii"))
        os.close(control_fd)
        _, status = os.waitpid(child, 0)
        os._exit(os.waitstatus_to_exitcode(status) if os.WIFEXITED(status) else 1)
    os.close(control_fd)
    # getppid is zero across this namespace boundary. The inherited pidfd instead
    # detects loss of the real bootstrap, closing the pre-prctl parent death race.
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise Stop("limits_unavailable")


def snapshot(fd):
    before = os.fstat(fd)
    with tempfile.TemporaryFile() as copied:
        total = 0
        while True:
            chunk = os.read(fd, min(65536, CAPS["input_bytes"] - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > CAPS["input_bytes"]:
                raise Stop("too_large")
            copied.write(chunk)
        after = os.fstat(fd)
        fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if (
            any(getattr(before, k) != getattr(after, k) for k in fields)
            or total != after.st_size
        ):
            raise Stop("changed")
        copied.seek(0)
        yield copied


def work(fd, kind, control_fd, limits):
    global CAPS
    CAPS = validated(limits)
    import ttree.documents

    ttree.documents.CAPS = CAPS
    metrics = {}
    try:
        # Install parent-death signal in bootstrap BEFORE containment so a dead
        # supervisor cannot leave a bootstrap. Handshake race addressed below.
        parent = os.getppid()
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) or os.getppid() != parent:
            raise Stop("limits_unavailable")
        resource.setrlimit(resource.RLIMIT_AS, (CAPS["address_space_bytes"],) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (CAPS["cpu_seconds"],) * 2)
        resource.setrlimit(resource.RLIMIT_FSIZE, (CAPS["response_bytes"],) * 2)
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # A pidfd opened before fork survives namespace creation. Poll it in PID1
        # after setting PDEATHSIG; a readable pidfd means the bootstrap has died.
        bootstrap_fd = os.pidfd_open(os.getpid())
        contain(control_fd)
        with selectors.DefaultSelector() as selector:
            selector.register(bootstrap_fd, selectors.EVENT_READ)
            if selector.select(0):
                os._exit(1)
        os.close(bootstrap_fd)
        for source in snapshot(fd):
            if kind == "docx":
                text, status = docx(source, metrics)
            elif kind == "pdf":
                text, status = pdf(source, metrics)
            else:
                raw = source.read(CAPS["input_bytes"] + 1)
                for bom, encoding in [
                    (b"\xff\xfe\0\0", "utf-32"),
                    (b"\0\0\xfe\xff", "utf-32"),
                    (b"\xff\xfe", "utf-16"),
                    (b"\xfe\xff", "utf-16"),
                    (b"\xef\xbb\xbf", "utf-8-sig"),
                ]:
                    if raw.startswith(bom):
                        text = raw.decode(encoding)
                        break
                else:
                    text = raw.decode("utf-8")
                if "\0" in text:
                    raise Stop("not_utf8")
                status = "counted"
            if len(text) > CAPS["characters"]:
                raise Stop("too_large")
            from ttree.tokenizer import LocalTokenizer

            tokenizer = LocalTokenizer(
                Path(__file__).parent / "data/o200k_base.tiktoken"
            )
            tokens = len(tokenizer.encode(text.encode()))
            result = dict(
                status=status
                if text or status != "counted"
                else ("empty" if kind == "text" else "no_text"),
                tokens=tokens,
                characters=len(text),
                **metrics,
            )
    except Stop as exc:
        result = dict(status=exc.status, tokens=None, **metrics)
    except ImportError:
        result = dict(status="reader_unavailable", tokens=None, **metrics)
    except UnicodeError:
        result = dict(status="not_utf8", tokens=None, **metrics)
    except Exception:
        result = dict(status="failed", tokens=None, **metrics)
    usage = resource.getrusage(resource.RUSAGE_SELF)
    result.update(
        cpu_seconds=round(usage.ru_utime + usage.ru_stime, 6),
        peak_rss_kib=usage.ru_maxrss,
    )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    work(int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), json.loads(sys.argv[4]))
