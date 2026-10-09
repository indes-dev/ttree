"""Disposable live path races, deep traversal and scan deadline."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from unittest import TestCase

from ttree.limits import validated
from ttree.scan import scan_roots


class SecurityTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_isolated_worker_ignores_caller_modules(self):
        # Run only against the corrected worker. Markers have no external effects.
        caller = self.root / "caller"
        caller.mkdir()
        marker = self.root / "local-module-imported"
        local = f"from pathlib import Path\nPath({str(marker)!r}).write_text('synthetic marker')\n"
        (caller / "ttree").mkdir()
        (caller / "ttree/__init__.py").write_text(local)
        for module in ("tiktoken", "pypdf", "ctypes", "json", "sitecustomize"):
            (caller / (module + ".py")).write_text(local)
        text = self.root / "normal.txt"
        text.write_text("Hello, world!")
        from test_documents import make_docx, make_pdf

        docx = self.root / "normal.docx"
        make_docx(docx, "<w:p><w:r><w:t>Readable DOCX text</w:t></w:r></w:p>")
        pdf = self.root / "normal.pdf"
        make_pdf(pdf, "Readable PDF text")
        # The installed console script imports its trusted package before workers
        # start; -m from the untrusted caller would test Python's parent bootstrap.
        result = subprocess.run(
            [
                str(Path(sys.executable).parent / "ttree"),
                "--json",
                "--strict",
                str(text),
                str(docx),
                str(pdf),
            ],
            cwd=caller,
            capture_output=True,
            text=True,
            timeout=10,
            env={"PATH": "/usr/bin", "LANG": "C.UTF-8", "TMPDIR": str(self.root)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [root["tokens"] for root in json.loads(result.stdout)["roots"]], [4, 4, 3]
        )
        self.assertFalse(marker.exists())
        self.assertEqual(result.stderr, "")

    def test_file_replacement_with_symlink_never_counts_outside(self):
        outside = self.root / "sentinel"
        outside.write_text("OUTSIDE-SENTINEL " * 1000)
        scanned = self.root / "scanned"
        scanned.mkdir()
        victim = scanned / "a.txt"
        victim.write_text("ok")
        parked = scanned / "parked"
        stopped = threading.Event()

        def mutate():
            while not stopped.is_set():
                try:
                    victim.rename(parked)
                    victim.symlink_to(outside)
                    time.sleep(0.001)
                    victim.unlink()
                    parked.rename(victim)
                    time.sleep(0.001)
                except FileNotFoundError:
                    pass

        thread = threading.Thread(target=mutate)
        thread.start()
        try:
            statuses = set()
            for _ in range(12):
                roots = scan_roots([str(victim)], validated(), time.monotonic() + 5)
                entry = roots[0][1][0]
                statuses.add(entry.status)
                self.assertIn(entry.tokens, (None, 1))
            self.assertTrue(statuses)
        finally:
            stopped.set()
            thread.join(2)
            self.assertFalse(thread.is_alive())

    def test_directory_replacement_with_symlink_never_counts_outside(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("OUTSIDE-SENTINEL " * 1000)
        scanned = self.root / "scanned"
        scanned.mkdir()
        victim = scanned / "dir"
        victim.mkdir()
        (victim / "a.txt").write_text("ok")
        parked = self.root / "parked-dir"
        stopped = threading.Event()

        def mutate():
            while not stopped.is_set():
                try:
                    victim.rename(parked)
                    victim.symlink_to(outside, target_is_directory=True)
                    time.sleep(0.001)
                    victim.unlink()
                    parked.rename(victim)
                    time.sleep(0.001)
                except FileNotFoundError:
                    pass

        thread = threading.Thread(target=mutate)
        thread.start()
        try:
            for _ in range(12):
                roots = scan_roots([str(scanned)], validated(), time.monotonic() + 5)
                for entry in roots[0][1]:
                    self.assertNotIn("secret.txt", entry.relative_path)
                    if entry.kind == "file":
                        self.assertIn(entry.tokens, (None, 1))
        finally:
            stopped.set()
            thread.join(2)
            self.assertFalse(thread.is_alive())

    def test_deeper_than_python_recursion_limit(self):
        tree = self.root / "deep"
        tree.mkdir()
        fd = os.open(tree, os.O_RDONLY | os.O_DIRECTORY)
        depth = 1100
        try:
            for _ in range(depth):
                os.mkdir("d", dir_fd=fd)
                new = os.open("d", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
                os.close(fd)
                fd = new
            result = subprocess.run(
                [sys.executable, "-m", "ttree.cli", "--json", "-L", "1", str(tree)],
                capture_output=True,
                text=True,
                timeout=45,
                env={**os.environ, "TMPDIR": str(self.root)},
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(len(value["roots"][0]["entries"]), depth + 1)
            self.assertTrue(value["total"]["complete"])
            human = subprocess.run(
                [sys.executable, "-m", "ttree.cli", "-L", "1", str(tree)],
                capture_output=True,
                text=True,
                timeout=45,
                env={**os.environ, "TMPDIR": str(self.root)},
            )
            self.assertEqual(human.returncode, 0)
            self.assertEqual(len(human.stdout.splitlines()), 2)
        finally:
            for _ in range(depth):
                parent = os.open("..", os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
                os.close(fd)
                os.rmdir("d", dir_fd=parent)
                fd = parent
            os.close(fd)

    def test_deadline_includes_tokenization_and_next_root_is_retained(self):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import DecodedStreamObject, NameObject
        from test_documents import make_pdf

        slow = self.root / "slow.pdf"
        make_pdf(slow, "x")
        writer = PdfWriter()
        writer.add_page(PdfReader(slow).pages[0])
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 1 Tf 1 1 Td (x) Tj ET\n" * 250000)
        writer.pages[0][NameObject("/Contents")] = writer._add_object(stream)
        writer.write(slow)
        later = self.root / "later.txt"
        later.write_text("Hello, world!")
        start = time.monotonic()
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ttree.cli",
                "--json",
                "--strict",
                "--limit-scan-seconds",
                "1",
                str(slow),
                str(later),
            ],
            capture_output=True,
            text=True,
            timeout=4,
            env={**os.environ, "TMPDIR": str(self.root)},
        )
        self.assertLess(time.monotonic() - start, 2.5)
        self.assertEqual(result.returncode, 3, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(len(value["roots"]), 2)
        self.assertFalse(value["total"]["complete"])
        self.assertEqual(value["roots"][0]["status"], "timed_out")
        self.assertEqual(value["roots"][1]["status"], "timed_out")

    def test_kernel_denied_namespace_fails_closed(self):
        # Disposable syscall filter in this child only: deny real unshare(2).
        # No host sysctl/permission change and no mocked availability result.
        import platform

        if sys.platform != "linux" or platform.machine() != "x86_64":
            self.skipTest("Linux x86_64 syscall fixture")
        source = self.root / "text.txt"
        source.write_text("Hello, world!")
        script = r"""
import ctypes,errno,sys
from ttree.cli import main
class Filter(ctypes.Structure):
    _fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint)]
class Program(ctypes.Structure):
    _fields_=[('len',ctypes.c_ushort),('filter',ctypes.POINTER(Filter))]
filters=(Filter*4)(Filter(0x20,0,0,0),Filter(0x15,0,1,272),Filter(0x06,0,0,0x50000|errno.EPERM),Filter(0x06,0,0,0x7fff0000))
program=Program(4,filters);libc=ctypes.CDLL(None,use_errno=True)
assert libc.prctl(38,1,0,0,0)==0
assert libc.prctl(22,2,ctypes.byref(program),0,0)==0
raise SystemExit(main(['--json','--strict',sys.argv[1]]))
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(source)],
            capture_output=True,
            text=True,
            timeout=4,
            env={**os.environ, "TMPDIR": str(self.root)},
        )
        self.assertEqual(result.returncode, 3, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["roots"][0]["status"], "limits_unavailable")
        self.assertIsNone(value["roots"][0]["tokens"])
        self.assertEqual(result.stderr, "")

    def test_unreadable_file_preserves_known_bytes(self):
        source = self.root / "unreadable.txt"
        source.write_text("secret")
        source.chmod(0)
        try:
            roots = scan_roots([str(source)], validated(), time.monotonic() + 5)
            entry = roots[0][1][0]
            self.assertEqual(
                (entry.kind, entry.bytes, entry.tokens, entry.status),
                ("file", 6, None, "unreadable"),
            )
        finally:
            source.chmod(0o600)

    def test_production_ipc_rejects_real_oversized_writer(self):
        from unittest.mock import patch

        from ttree.bounded import count_fd

        source = self.root / "source.txt"
        source.write_text("x")
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        real_start = subprocess.Popen
        script = """
import os,resource,signal,sys
from ttree.worker import contain
resource.setrlimit(resource.RLIMIT_AS,(512*1024*1024,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(10,)*2)
contain(int(sys.argv[2]))
for _ in range(193):os.write(1,b'X'*65536)
"""

        def launch(command, **kwargs):
            position = command.index("ttree.worker")
            return real_start(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    script,
                    command[position + 1],
                    command[position + 3],
                ],
                **kwargs,
            )

        try:
            # Substitute the trusted entrypoint only; stdout, limits, process,
            # namespace and coordinator boundary are all actual execution.
            with patch("ttree.bounded.subprocess.Popen", side_effect=launch):
                result = count_fd(fd, "text", validated(), time.monotonic() + 5)
            self.assertEqual(result, {"status": "too_large", "tokens": None})
        finally:
            os.close(fd)

    def test_production_timeout_waits_for_setsid_descendant(self):
        from unittest.mock import patch

        from ttree.bounded import count_fd

        marker = self.root / "marker"
        source = self.root / "source.txt"
        source.write_text(str(marker))
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
        real_start = subprocess.Popen
        script = """
import json,os,sys,time
from pathlib import Path
from ttree.worker import contain
contain(int(sys.argv[2]))
marker=Path(os.read(int(sys.argv[1]),4096).decode())
if os.fork()==0:
 os.setsid()
 raw=Path('/proc/self/stat').read_text();fields=raw.rsplit(')',1)[1].split()
 marker.write_text(json.dumps({'pid':int(raw.split()[0]),'starttime':fields[19],'session':fields[3]}))
 time.sleep(10);os._exit(0)
time.sleep(10)
"""

        def launch(command, **kwargs):
            position = command.index("ttree.worker")
            return real_start(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    script,
                    command[position + 1],
                    command[position + 3],
                ],
                **kwargs,
            )

        limits = validated({"wall_seconds": 1})
        try:
            with patch("ttree.bounded.subprocess.Popen", side_effect=launch):
                result = count_fd(fd, "text", limits, time.monotonic() + 5)
            self.assertEqual(result["status"], "timed_out")
            identity = json.loads(marker.read_text())
            self.assertEqual(str(identity["pid"]), identity["session"])
            try:
                fields = (
                    (Path("/proc") / str(identity["pid"]) / "stat")
                    .read_text()
                    .rsplit(")", 1)[1]
                    .split()
                )
                self.assertTrue(fields[19] != identity["starttime"] or fields[0] == "Z")
            except FileNotFoundError:
                pass
        finally:
            os.close(fd)

    def test_coordinator_death_before_worker_start_fails_closed(self):
        source = self.root / "text.txt"
        source.write_text("Hello, world!")
        # The real coordinator exits while its child waits before exec. The worker
        # must reject adoption by another process instead of watching its new parent.
        script = r"""
import json,os,sys,time
from ttree.limits import validated
fd=os.open(sys.argv[1],os.O_RDONLY|os.O_NOFOLLOW);os.set_inheritable(fd,True)
read,write=os.pipe();os.set_inheritable(write,True)
expected=os.getpid()
if os.fork()==0:
 time.sleep(.1)
 os.execv(sys.executable,[sys.executable,'-I','-m','ttree.worker',str(fd),'text',str(write),json.dumps(validated()),str(expected)])
os._exit(0)
"""
        result = subprocess.run(
            [sys.executable, "-c", script, str(source)],
            capture_output=True,
            text=True,
            timeout=3,
            env={**os.environ, "TMPDIR": str(self.root)},
        )
        self.assertEqual(result.returncode, 0)
        value = json.loads(result.stdout)
        self.assertEqual(value["status"], "limits_unavailable")
        self.assertIsNone(value["tokens"])
        self.assertEqual(result.stderr, "")

    def test_dotdot_reparent_race_never_reads_new_outside_parent(self):
        from unittest.mock import patch

        scanned = self.root / "scanned"
        scanned.mkdir()
        (scanned / "bar.txt").write_text("ok")
        victim = scanned / "foo"
        victim.mkdir()
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "bar.txt").write_text("OUTSIDE-SENTINEL " * 1000)
        moved = outside / "moved"
        trigger = threading.Event()
        done = threading.Event()

        def mutate():
            if trigger.wait(2):
                victim.rename(moved)
            done.set()

        thread = threading.Thread(target=mutate)
        thread.start()
        real_open = os.open
        injected = False

        def race_open(path, *args, **kwargs):
            nonlocal injected
            fd = real_open(path, *args, **kwargs)
            if path == "foo" and not injected:
                injected = True
                trigger.set()
                self.assertTrue(done.wait(2))
            return fd

        try:
            # Scheduling hook only; all opens, rename, FD traversal and worker
            # reads are real. The old '..' read traversed moved/'..'/bar.txt.
            with patch("ttree.scan.os.open", side_effect=race_open):
                roots = scan_roots(
                    [str(victim) + "/../bar.txt"], validated(), time.monotonic() + 5
                )
            self.assertTrue(injected)
            self.assertEqual(roots[0][1][0].tokens, 1)
        finally:
            trigger.set()
            thread.join(2)

    def test_unreadable_descendant_is_not_misclassified_as_replaced(self):
        source = self.root / "unreadable.txt"
        source.write_text("secret")
        source.chmod(0)
        try:
            roots = scan_roots([str(self.root)], validated(), time.monotonic() + 5)
            entry = next(item for item in roots[0][1] if item.name == "unreadable.txt")
            self.assertEqual(
                (entry.status, entry.tokens, entry.bytes), ("unreadable", None, 6)
            )
            self.assertFalse(roots[0][1][0].complete)
        finally:
            source.chmod(0o600)
