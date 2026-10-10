"""Private bounded base worker; no native adapter or external commands."""

from __future__ import annotations

import ctypes
import errno
import json
import os
import platform
import resource
import selectors
import signal
import sys
import tempfile
from pathlib import Path

from ttree.documents import Stop, doc, docx, pdf
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
        # Restricted hosts can use a single-process syscall sandbox. With fork,
        # clone, exec and networking denied there are no descendants to escape
        # the supervisor's process limits or cleanup. Never run uncontained.
        single_process_filter(libc)
        os.close(control_fd)
        return False
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
    return True


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


def work(fd, kind, control_fd, limits, expected_parent):
    global CAPS
    CAPS = validated(limits)
    import ttree.documents

    ttree.documents.CAPS = CAPS
    metrics = {}
    try:
        # Install parent-death signal in bootstrap BEFORE containment so a dead
        # supervisor cannot leave a bootstrap. Handshake race addressed below.
        parent = expected_parent
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(1, signal.SIGKILL, 0, 0, 0) or os.getppid() != parent:
            raise Stop("limits_unavailable")
        resource.setrlimit(resource.RLIMIT_AS, (CAPS["address_space_bytes"],) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (CAPS["cpu_seconds"],) * 2)
        # Snapshot storage follows the input ceiling, independently of IPC.
        # The snapshot loop rejects excess input before writing it.
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (max(CAPS["input_bytes"], CAPS["response_bytes"]),) * 2,
        )
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        # A pidfd opened before fork survives namespace creation. Poll it in PID1
        # after setting PDEATHSIG; a readable pidfd means the bootstrap has died.
        bootstrap_fd = os.pidfd_open(os.getpid())
        contained = contain(control_fd)
        if contained and platform.machine() == "x86_64":
            single_process_filter(libc)
        if contained:
            with selectors.DefaultSelector() as selector:
                selector.register(bootstrap_fd, selectors.EVENT_READ)
                if selector.select(0):
                    os._exit(1)
        os.close(bootstrap_fd)
        for source in snapshot(fd):
            # Parsers read the completed snapshot. Subsequent
            # output files have the smaller finite output ceiling; IPC also has
            # its own incremental supervisor byte counter.
            resource.setrlimit(resource.RLIMIT_FSIZE, (CAPS["response_bytes"],) * 2)
            if kind == "doc":
                text, status = doc(source, metrics)
            elif kind == "docx":
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


def single_process_filter(libc):
    """Finite Linux x86_64 syscall allowlist; deny process creation and networking.

    This is for static Python readers only. No converter runs in this mode.
    Fail closed on another ABI; reject x32 and all alternate audit architectures.
    """
    if platform.machine() != "x86_64":
        raise Stop("limits_unavailable")

    class Filter(ctypes.Structure):
        _fields_ = [
            ("code", ctypes.c_ushort),
            ("jt", ctypes.c_ubyte),
            ("jf", ctypes.c_ubyte),
            ("k", ctypes.c_uint),
        ]

    class Program(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]

    # Linux x86_64 ABI, asm/unistd_64.h. No socket, fork/vfork/clone/clone3,
    # execve/execveat, ptrace, process_vm_*, pidfd_getfd or io_uring operations.
    allowed = (
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16,
        17,
        18,
        19,
        20,
        21,
        24,
        25,
        28,
        32,
        33,
        35,
        39,
        60,
        63,
        72,
        74,
        75,
        77,
        79,
        87,
        89,
        95,
        97,
        98,
        99,
        102,
        104,
        107,
        108,
        110,
        131,
        137,
        138,
        157,
        158,
        186,
        202,
        204,
        217,
        218,
        228,
        230,
        231,
        232,
        233,
        257,
        262,
        263,
        267,
        269,
        270,
        271,
        273,
        281,
        291,
        302,
        318,
        332,
        334,
        436,
        439,
    )
    instructions = [
        Filter(0x20, 0, 0, 4),
        Filter(0x15, 1, 0, 0xC000003E),
        Filter(0x06, 0, 0, 0x80000000),
        Filter(0x20, 0, 0, 0),
    ]
    for call in allowed:
        instructions.extend((Filter(0x15, 0, 1, call), Filter(0x06, 0, 0, 0x7FFF0000)))
    instructions.append(Filter(0x06, 0, 0, 0x50000 | errno.EPERM))
    filters = (Filter * len(instructions))(*instructions)
    program = Program(len(filters), filters)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise Stop("limits_unavailable")


if __name__ == "__main__":
    work(
        int(sys.argv[1]),
        sys.argv[2],
        int(sys.argv[3]),
        json.loads(sys.argv[4]),
        int(sys.argv[5]),
    )
