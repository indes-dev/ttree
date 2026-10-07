"""Independent base feasibility candidate; not wired into the public CLI.

Linux namespace containment uses libc/kernel primitives, not a host command.
Only a small scalar response crosses the worker boundary. TASK-003 original caps.
"""
from __future__ import annotations

import ctypes
import json
import logging
import os
import resource
import selectors
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from xml.parsers import expat
from zipfile import ZipFile

MIB = 1024 * 1024
CAPS = dict(input_bytes=64*MIB, xml_part_bytes=4*MIB, xml_total_bytes=8*MIB,
            pdf_pages=2000, characters=1_000_000, wall_seconds=15,
            cpu_seconds=10, address_space_bytes=512*MIB, response_bytes=12*MIB,
            scan_seconds=120, entries=100_000, xml_depth=128,
            xml_elements=100_000, zip_members=4096)
ROOT = Path(__file__).resolve().parents[2]


class Stop(Exception):
    def __init__(self, status):
        self.status = status


def contain(control_fd):
    """Kill namespace descendants even if they fork/setsid/reparent.

    Bootstrap waits for namespace PID 1. PID 1's parent-death signal kills the
    namespace on supervisor termination; check parent identity after prctl to
    close the installation race. Kernel PID namespace teardown kills all members.
    """
    if sys.platform != 'linux':
        raise Stop('limits_unavailable')
    uid, gid = os.getuid(), os.getgid()
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.unshare(0x10000000) != 0:
        raise Stop('limits_unavailable')
    try:
        Path('/proc/self/setgroups').write_text('deny')
        Path('/proc/self/uid_map').write_text(f'0 {uid} 1')
        Path('/proc/self/gid_map').write_text(f'0 {gid} 1')
    except OSError:
        raise Stop('limits_unavailable') from None
    if libc.unshare(0x20000000) != 0:
        raise Stop('limits_unavailable')
    child = os.fork()
    if child:
        os.write(control_fd,str(child).encode('ascii'))
        os.close(control_fd)
        _, status = os.waitpid(child, 0)
        os._exit(os.waitstatus_to_exitcode(status) if os.WIFEXITED(status) else 1)
    os.close(control_fd)
    # getppid is zero across this namespace boundary. The inherited pidfd instead
    # detects loss of the real bootstrap, closing the pre-prctl parent death race.
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0:
        raise Stop('limits_unavailable')


def run(path: Path, kind: str, *, wall=15, response_cap=12*MIB):
    """Open once without following links; reader snapshots this exact descriptor."""
    started = time.monotonic()
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return dict(status='unreadable', tokens=None)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return dict(status='unreadable', tokens=None)
        if info.st_size > CAPS['input_bytes']:
            return dict(status='too_large', tokens=None, bytes=info.st_size)
        control_read,control_write=os.pipe()
        namespace_fd=None
        command = [sys.executable, str(Path(__file__).resolve()), 'child', str(fd), kind,str(control_write)]
        with subprocess.Popen(command, pass_fds=(fd,control_write), stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, env={'PATH':'/usr/bin','LANG':'C.UTF-8','TMPDIR':str(ROOT/'.tmp')}) as process:
            os.close(control_write)
            output = bytearray()
            status = None
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                selector.register(control_read, selectors.EVENT_READ)
                while True:
                    remaining = wall - (time.monotonic() - started)
                    if remaining <= 0:
                        status = 'timed_out'
                        break
                    events = selector.select(min(.05, remaining))
                    if not events:
                        continue
                    for key,_ in events:
                        if key.fd==control_read:
                            identity=os.read(control_read,32)
                            selector.unregister(control_read)
                            if identity:
                                try:namespace_fd=os.pidfd_open(int(identity))
                                except ProcessLookupError:pass
                    if not any(key.fd==process.stdout.fileno() for key,_ in events):
                        continue
                    chunk = os.read(process.stdout.fileno(), min(65536, response_cap-len(output)+1))
                    if not chunk:
                        break
                    if len(output) + len(chunk) > response_cap:
                        status = 'too_large'
                        break
                    output.extend(chunk)
            if status:
                process.kill()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            namespace_terminated=True
            if namespace_fd is not None:
                with selectors.DefaultSelector() as cleanup:
                    cleanup.register(namespace_fd,selectors.EVENT_READ)
                    namespace_terminated=bool(cleanup.select(2))
                os.close(namespace_fd)
            os.close(control_read)
            if not namespace_terminated:
                status='limits_unavailable'
            if status:
                result = dict(status=status, tokens=None)
            elif process.returncode:
                result = dict(status='failed', tokens=None)
            else:
                try:
                    result = json.loads(output)
                    if not isinstance(result, dict) or result.get('status') not in {
                        'counted','empty','no_text','partial','failed','too_large',
                        'encrypted','limits_unavailable','not_utf8'}:
                        raise ValueError
                except (ValueError, UnicodeError):
                    result = dict(status='failed', tokens=None)
            result.update(bytes=info.st_size, seconds=round(time.monotonic()-started,4),
                          ipc_bytes_received=len(output)+(len(chunk) if status=='too_large' else 0),
                          bootstrap_pid=process.pid, bootstrap_reaped=process.returncode is not None, namespace_terminated=namespace_terminated)
            return result
    finally:
        os.close(fd)


def snapshot(fd):
    before = os.fstat(fd)
    with tempfile.TemporaryFile() as copied:
        total = 0
        while True:
            chunk = os.read(fd, min(65536, CAPS['input_bytes']-total+1))
            if not chunk:
                break
            total += len(chunk)
            if total > CAPS['input_bytes']:
                raise Stop('too_large')
            copied.write(chunk)
        after = os.fstat(fd)
        fields = ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
        if any(getattr(before,k) != getattr(after,k) for k in fields) or total != after.st_size:
            raise Stop('failed')
        copied.seek(0)
        yield copied


def docx(source, metrics):
    chunks = []
    characters = elements = actual = 0
    with ZipFile(source) as archive:
        names = archive.namelist()
        if len(names) > CAPS['zip_members']:
            raise Stop('too_large')
        if len(names) != len(set(names)):
            raise Stop('failed')
        selected = ['word/document.xml'] + sorted(n for n in names if
            n.startswith('word/') and (n.startswith(('word/header','word/footer')) or
                                      n in ('word/footnotes.xml','word/endnotes.xml')) and n.endswith('.xml'))
        for name in selected:
            parser = expat.ParserCreate(namespace_separator='}')
            depth = 0
            text_depth = 0
            part_bytes = 0
            def start(tag, attrs):
                nonlocal depth, elements, text_depth
                depth += 1
                elements += 1
                metrics.update(xml_elements=elements, xml_depth_peak=max(metrics.get('xml_depth_peak',0),depth))
                if depth > CAPS['xml_depth'] or elements > CAPS['xml_elements']:
                    raise Stop('too_large')
                if tag.endswith('}t'):
                    text_depth = depth
            def end(tag):
                nonlocal depth, text_depth
                if depth == text_depth:
                    text_depth = 0
                if tag.endswith('}p'):
                    append('\n')
                depth -= 1
            def append(data):
                nonlocal characters
                characters += len(data)
                if characters > CAPS['characters']:
                    raise Stop('too_large')
                chunks.append(data)
            def text(data):
                if text_depth:
                    append(data)
            def reject(*args):
                raise Stop('failed')
            parser.StartElementHandler = start
            parser.EndElementHandler = end
            parser.CharacterDataHandler = text
            parser.StartDoctypeDeclHandler = reject
            parser.EntityDeclHandler = reject
            parser.ExternalEntityRefHandler = reject
            with archive.open(name) as stream:
                while True:
                    block = stream.read(min(65536, CAPS['xml_part_bytes']-part_bytes+1,
                                            CAPS['xml_total_bytes']-actual+1))
                    if not block:
                        break
                    part_bytes += len(block)
                    actual += len(block)
                    metrics['actual_xml_bytes'] = actual
                    if part_bytes > CAPS['xml_part_bytes'] or actual > CAPS['xml_total_bytes']:
                        raise Stop('too_large')
                    parser.Parse(block, False)
                parser.Parse(b'', True)
            chunks.append('\n')
    return ''.join(chunks).strip(), 'counted'


def pdf(source, metrics):
    from pypdf import PdfReader
    class Warnings(logging.Handler):
        def emit(self, record):
            # Count without formatting record arguments/document fragments.
            metrics['pdf_warnings'] = metrics.get('pdf_warnings',0)+1
    logger = logging.getLogger('pypdf')
    previous = logger.level, logger.propagate, logger.handlers[:]
    logger.setLevel(logging.WARNING)
    logger.propagate = False
    logger.handlers = [Warnings(logging.WARNING)]
    parts = []
    status = 'counted'
    chars = 0
    try:
        reader = PdfReader(source)
        if reader.is_encrypted:
            if not reader.decrypt(''):
                raise Stop('encrypted')
        if len(reader.pages) > CAPS['pdf_pages']:
            raise Stop('too_large')
        for page in reader.pages:
            try:
                text = page.extract_text() or ''
                chars += len(text)
                if chars > CAPS['characters']:
                    raise Stop('too_large')
                parts.append(text)
            except Stop:
                raise
            except Exception:
                status = 'partial'
        if metrics.get('pdf_warnings'):
            status = 'partial'
    finally:
        logger.setLevel(previous[0])
        logger.propagate, logger.handlers = previous[1:]
    return '\n\n'.join(parts), status


def work(fd, kind, control_fd):
    metrics = {}
    try:
        # Install parent-death signal in bootstrap BEFORE containment so a dead
        # supervisor cannot leave a bootstrap. Handshake race addressed below.
        parent = os.getppid()
        libc = ctypes.CDLL(None,use_errno=True)
        if libc.prctl(1,signal.SIGKILL,0,0,0) or os.getppid()!=parent:
            raise Stop('limits_unavailable')
        resource.setrlimit(resource.RLIMIT_AS,(512*MIB,512*MIB))
        resource.setrlimit(resource.RLIMIT_CPU,(10,10))
        resource.setrlimit(resource.RLIMIT_FSIZE,(12*MIB,12*MIB))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        # A pidfd opened before fork survives namespace creation. Poll it in PID1
        # after setting PDEATHSIG; a readable pidfd means the bootstrap has died.
        bootstrap_fd = os.pidfd_open(os.getpid())
        contain(control_fd)
        with selectors.DefaultSelector() as selector:
            selector.register(bootstrap_fd,selectors.EVENT_READ)
            if selector.select(0):
                os._exit(1)
        os.close(bootstrap_fd)
        if kind=='timeout':
            time.sleep(30)
        if kind=='oversized':
            block=b'X'*65536
            for _ in range(193):
                os.write(1,block)
            return
        if kind=='cpu':
            while True: pass
        if kind=='memory':
            allocation=bytearray(600*MIB)
        if kind=='crash':
            os._exit(7)
        if kind=='escaped':
            child=os.fork()
            if child==0:
                os.setsid()
                # Inherited source fd carries only this synthetic marker path.
                target=os.read(fd,1024).decode()
                Path(target).write_text(str(os.getpid()))
                time.sleep(30)
                Path(target+'.survived').write_text('escaped')
                os._exit(0)
            time.sleep(30)
        for source in snapshot(fd):
            if kind=='docx':
                text,status=docx(source,metrics)
            elif kind=='pdf':
                text,status=pdf(source,metrics)
            else:
                raw=source.read(CAPS['input_bytes']+1)
                for bom,encoding in [(b'\xff\xfe\0\0','utf-32'),(b'\0\0\xfe\xff','utf-32'),
                                     (b'\xff\xfe','utf-16'),(b'\xfe\xff','utf-16'),(b'\xef\xbb\xbf','utf-8-sig')]:
                    if raw.startswith(bom):
                        text=raw.decode(encoding);break
                else:
                    text=raw.decode('utf-8')
                if '\0' in text:
                    raise Stop('not_utf8')
                status='counted'
            if len(text)>CAPS['characters']:
                raise Stop('too_large')
            sys.path.insert(0,str(ROOT/'src'))
            from ttree.tokenizer import LocalTokenizer
            tokenizer=LocalTokenizer(ROOT/'src/ttree/data/o200k_base.tiktoken')
            tokens=len(tokenizer.encode(text.encode()))
            result=dict(status=status if text else ('empty' if kind=='text' else 'no_text'),
                        tokens=tokens,characters=len(text),**metrics)
    except Stop as exc:
        result=dict(status=exc.status,tokens=None,**metrics)
    except UnicodeError:
        result=dict(status='not_utf8',tokens=None,**metrics)
    except Exception:
        result=dict(status='failed',tokens=None,**metrics)
    usage=resource.getrusage(resource.RUSAGE_SELF)
    result.update(cpu_seconds=round(usage.ru_utime+usage.ru_stime,6),peak_rss_kib=usage.ru_maxrss)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    work(int(sys.argv[2]),sys.argv[3],int(sys.argv[4]))
