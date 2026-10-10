"""Bounded synthetic TASK-003 feasibility probe. No production integration.

Run via run_prototype.sh, inside an outer disposable PID/network namespace.
No real external requests, private documents, or inherited reader environment.
"""
from __future__ import annotations

import http.server
import json
import os
import resource
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

MIB = 1024 * 1024
OLE = bytes.fromhex("d0cf11e0a1b11ae1")
ROOT = Path(__file__).resolve().parents[2]
READER = "/usr/lib/libreoffice/program/soffice.bin" if "--direct-reader" in sys.argv else "/usr/bin/libreoffice"


def limits(memory: int, cpu: int) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (memory * MIB, memory * MIB))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_FSIZE, (12 * MIB, 12 * MIB))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run(command: list[str], work: Path, name: str, *, wall=20.0, cpu=15, memory=768) -> dict:
    start = time.monotonic()
    peak_tree_rss = 0
    peak_process_vms = 0
    with (work / (name + ".out")).open("wb") as out, (work / (name + ".err")).open("wb") as err:
        child = subprocess.Popen(command, stdout=out, stderr=err, start_new_session=True,
                                 env={"PATH": "/usr/bin", "LANG": "C.UTF-8"},
                                 preexec_fn=lambda: limits(memory, cpu))
        timed_out = False
        while True:
            # Sample only this child tree in the outer private /proc. wait4 below
            # reports the wrapper; reaped namespace descendants are not included.
            processes = {}
            for folder in Path("/proc").iterdir():
                if not folder.name.isdigit():
                    continue
                try:
                    values = (folder / "stat").read_text().rsplit(")", 1)[1].split()
                    mem = (folder / "statm").read_text().split()
                    processes[int(folder.name)] = (int(values[1]), int(mem[0]) * 4, int(mem[1]) * 4)
                except (OSError, ValueError):
                    continue
            tree = {child.pid}
            while True:
                more = {pid for pid, values in processes.items() if values[0] in tree}
                if more <= tree:
                    break
                tree |= more
            peak_tree_rss = max(peak_tree_rss, sum(processes[p][2] for p in tree if p in processes))
            peak_process_vms = max(peak_process_vms, max((processes[p][1] for p in tree if p in processes), default=0))
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                child.returncode = os.waitstatus_to_exitcode(status)
                break
            if time.monotonic() - start >= wall:
                timed_out = True
                os.killpg(child.pid, signal.SIGKILL)
                _, status, usage = os.wait4(child.pid, 0)
                child.returncode = os.waitstatus_to_exitcode(status)
                break
            time.sleep(0.01)
    return {"command": command, "returncode": child.returncode, "timed_out": timed_out,
            "seconds": round(time.monotonic() - start, 4),
            "cpu_seconds": round(usage.ru_utime + usage.ru_stime, 4),
            "wrapper_wait4_peak_rss_kib": usage.ru_maxrss,
            "sampled_peak_tree_rss_kib": peak_tree_rss,
            "sampled_peak_process_vms_kib": peak_process_vms,
            "limits": {"wall_seconds": wall, "cpu_seconds_per_process": cpu,
                       "address_space_mib_per_process": memory, "response_bytes": 12 * MIB}}


def sandbox(work: Path, command: list[str], *, network=True, disable_userns=False) -> list[str]:
    # Static distribution runtime only. No host /etc, home, run, tmp or sockets.
    args = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
            "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "--dir", "/etc",
            "--ro-bind", "/etc/fonts", "/etc/fonts",
            "--ro-bind", "/etc/libreoffice/bootstraprc", "/etc/libreoffice/bootstraprc",
            "--ro-bind", "/etc/libreoffice/sofficerc", "/etc/libreoffice/sofficerc",
            "--bind", str(work), "/work", "--symlink", "/work/tmp", "/tmp",
            "--chdir", "/work", "--clearenv",
            "--setenv", "PATH", "/usr/bin", "--setenv", "HOME", "/work/home",
            "--setenv", "TMPDIR", "/work/tmp", "--setenv", "LANG", "C.UTF-8",
            "--setenv", "SAL_USE_VCLPLUGIN", "svp",
            "--setenv", "MALLOC_ARENA_MAX", "1"]
    if not network:
        # Positive control only; inherits the outer disposable loopback namespace.
        args.append("--share-net")
    if disable_userns:
        args.append("--disable-userns")
    return args + ["--"] + command


def reader(work: Path, source: str, target: str, *, word_filter=False) -> list[str]:
    command = [READER, "-env:UserInstallation=file:///work/profile",
               "--headless", "--nologo", "--nodefault", "--norestore"]
    if word_filter:
        command.append("--infilter=MS Word 97")
    return sandbox(work, command + ["--convert-to", target, "--outdir", "/work/output", source])


def fresh(root: Path, name: str) -> Path:
    work = root / name
    for folder in ("home", "tmp", "profile/user", "output"):
        (work / folder).mkdir(parents=True, exist_ok=True)
    work.chmod(0o700)
    return work


def worker(path: Path, kind: str) -> None:
    # Parsing+tokenization live in the bounded child. Only scalar JSON returns.
    sys.path.insert(0, str(ROOT / "src"))
    from ttree.tokenizer import LocalTokenizer
    if kind == "docx":
        from xml.parsers import expat
        actual = 0
        depth = 0
        elements = 0
        chars = 0
        chunks = []
        parser = expat.ParserCreate(namespace_separator="}")
        in_text = False

        def start(name, attrs):
            nonlocal depth, elements, in_text
            depth += 1
            elements += 1
            if depth > 128 or elements > 100_000:
                raise ValueError("structural cap")
            in_text = name.endswith("}t")

        def end(name):
            nonlocal depth, in_text
            depth -= 1
            if name.endswith("}t"):
                in_text = False

        def text(data):
            nonlocal chars
            if in_text:
                chars += len(data)
                if chars > 1_000_000:
                    raise ValueError("character cap")
                chunks.append(data)

        def reject(*args):
            raise ValueError("XML declaration")

        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.CharacterDataHandler = text
        parser.StartDoctypeDeclHandler = reject
        parser.EntityDeclHandler = reject
        try:
            with ZipFile(path) as archive:
                if len(archive.infolist()) > 4096:
                    raise ValueError("member cap")
                with archive.open("word/document.xml") as source:
                    while True:
                        chunk = source.read(min(65536, 4 * MIB - actual + 1))
                        if not chunk:
                            break
                        actual += len(chunk)
                        if actual > 4 * MIB:
                            raise ValueError("actual expansion cap")
                        parser.Parse(chunk, False)
                    parser.Parse(b"", True)
            text_value = "".join(chunks)
        except Exception:
            print(json.dumps({"status": "too_large", "actual_xml_bytes": actual,
                              "elements": elements, "depth": depth}))
            return
    else:
        from ttree.documents import extract_pdf
        text_value = extract_pdf(path).text
    tokenizer = LocalTokenizer(ROOT / "src/ttree/data/o200k_base.tiktoken")
    count = len(tokenizer.encode(text_value.encode()))
    print(json.dumps({"status": "counted", "tokens": count, "characters": len(text_value)}))


def main(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["/usr/bin/ip", "link", "set", "lo", "up"], check=True)
    cases = {}
    checks = {}
    report = {"start_sha": "558f7d7f13bd428e85829f86c0f21c30eb9b5126",
              "python": sys.version, "host": socket.gethostname(), "cases": cases, "checks": checks,
              "scope": "synthetic; outer user/PID/network namespace; no real external requests"}
    report["versions"] = {
        "kernel": os.uname().release,
        "bubblewrap": subprocess.run(["/usr/bin/bwrap", "--version"], capture_output=True, text=True, timeout=2).stdout.strip(),
        "libreoffice": subprocess.run(["/usr/bin/libreoffice", "--version"], capture_output=True, text=True, timeout=2).stdout.strip(),
    }
    report["reader_entrypoint"] = READER

    def record(name, command, work, **kw):
        cases[name] = run(command, work, name, **kw)
        return cases[name]

    def save():
        (root / "results.json").write_text(json.dumps(report, indent=2) + "\n")

    try:
        gen = fresh(root, "generate")
        (gen / "source.txt").write_text("Synthetic legacy Word document text for TASK-003.\n")
        result = record("generate_doc", reader(gen, "/work/source.txt", "doc:MS Word 97"), gen)
        doc = gen / "output/source.doc"
        checks["real_doc_created"] = result["returncode"] == 0 and doc.exists() and doc.read_bytes()[:8] == OLE
        if not checks["real_doc_created"]:
            raise RuntimeError("real DOC generation failed within boundary")
        conv = fresh(root, "convert")
        (conv / "input.doc").write_bytes(doc.read_bytes())
        (conv / "profile/user/registrymodifications.xcu").write_text(
            '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
            '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
            '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>'
            '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>'
            '<prop oor:name="DisableActiveContent" oor:op="fuse"><value>true</value></prop></item>'
            '<item oor:path="/org.openoffice.Office.Writer/Content/Update">'
            '<prop oor:name="Link" oor:op="fuse"><value>2</value></prop>'
            '<prop oor:name="Field" oor:op="fuse"><value>false</value></prop></item></oor:items>')
        result = record("real_doc", reader(conv, "/work/input.doc", "txt:Text (encoded):UTF8", word_filter=True), conv)
        out = conv / "output/input.txt"
        checks["real_doc_text"] = result["returncode"] == 0 and out.exists() and "Synthetic legacy Word" in out.read_text(encoding="utf-8-sig")
        if not checks["real_doc_text"]:
            raise RuntimeError("real DOC conversion failed within boundary")

        # Helper controls use only a synthetic sentinel and outer loopback.
        sentinel = root / "sentinel.txt"
        sentinel.write_text("SYNTHETIC-HOST-SENTINEL")
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"SYNTHETIC-LOOPBACK")

            def log_message(self, *args):
                pass

        with http.server.HTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_address[1]
            helper = (
                "import json,os,socket; from pathlib import Path; "
                "s=socket.socket(); s.settimeout(.25); "
                f"print(json.dumps({{'host_file':Path({str(sentinel)!r}).exists(),"
                f"'connect':s.connect_ex(('127.0.0.1',{port}))==0,"
                "'pids':len([p for p in Path('/proc').iterdir() if p.name.isdigit()]),"
                "'host_env':os.getenv('TASK003_CANARY')}))"
            )
            probe = fresh(root, "helper")
            record("helper_positive", ["/usr/bin/python3.14", "-c", helper], probe, wall=2, cpu=1, memory=512)
            record("helper_isolated", sandbox(probe, ["/usr/bin/python3.14", "-c", helper]), probe, wall=2, cpu=1, memory=512)
            positive = json.loads((probe / "helper_positive.out").read_text())
            isolated = json.loads((probe / "helper_isolated.out").read_text())
            checks["helper_positive_live"] = positive["host_file"] and positive["connect"]
            checks["helper_boundary"] = not isolated["host_file"] and not isolated["connect"] and isolated["pids"] <= 4 and isolated["host_env"] is None

            # A real native-reader control known to activate network in TASK-002.
            # It remains inside the outer disposable loopback network namespace.
            native = fresh(root, "native-control")
            (native / "input.html").write_text(f'<html><head><link rel="stylesheet" href="http://127.0.0.1:{port}/synthetic"></head><body>Native control</body></html>')
            args = [READER, "-env:UserInstallation=file:///work/profile", "--headless", "--norestore", "--convert-to", "txt:Text (encoded):UTF8", "--outdir", "/work/output", "/work/input.html"]
            record("native_network_positive", sandbox(native, args, network=False), native)
            checks["native_network_positive_live"] = bool(requests)
            requests.clear()
            denied = fresh(root, "native-denied")
            (denied / "input.html").write_bytes((native / "input.html").read_bytes())
            record("native_network_denied", sandbox(denied, args), denied)
            checks["native_network_denied"] = not requests
            server.shutdown()
            thread.join(timeout=1)

        denied = fresh(root, "denied-userns")
        inner = sandbox(denied, ["/usr/bin/true"])
        # Paths in the nested command are private sandbox paths.
        inner[inner.index(str(denied))] = "/work"
        result = record("denied_userns", sandbox(denied, inner, disable_userns=True), denied, wall=2, cpu=1, memory=512)
        checks["denied_userns_fails"] = result["returncode"] != 0
        checks["missing_boundary_fails"] = not Path("/nonexistent/task003/bwrap").exists()

        escape = fresh(root, "escape")
        script = "import os,time; from pathlib import Path; p=os.fork(); (os.setsid() if p==0 else None); Path('/work/child.pid').write_text(str(os.getpid())) if p==0 else None; time.sleep(5)"
        result = record("setsid_timeout", sandbox(escape, ["/usr/bin/python3.14", "-c", script]), escape, wall=.4, cpu=1, memory=512)
        checks["setsid_killed"] = result["timed_out"] and (escape / "child.pid").exists()
        # Namespace destruction is checked using a unique argv marker in outer /proc.
        time.sleep(.1)
        checks["no_escaped_process"] = not any(
            b"/work/child.pid" in (p / "cmdline").read_bytes()
            for p in Path("/proc").iterdir() if p.name.isdigit() and (p / "cmdline").exists()
        )
        timeout_work = fresh(root, "reader-timeout")
        (timeout_work / "input.doc").write_bytes(doc.read_bytes())
        result = record("real_reader_timeout", reader(timeout_work, "/work/input.doc", "txt:Text (encoded):UTF8", word_filter=True), timeout_work, wall=.05)
        checks["real_reader_timed_out"] = result["timed_out"]
        checks["no_host_tmp"] = not any(p.name.startswith("lu") for p in Path("/tmp").iterdir())

        fixtures = fresh(root, "workers")
        wns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        for name, body in (("normal", "Hello DOCX"), ("scaled", "A" * (5 * MIB))):
            with ZipFile(fixtures / (name + ".docx"), "w", ZIP_DEFLATED) as archive:
                archive.writestr("word/document.xml", f'<w:document xmlns:w="{wns}"><w:body><w:p><w:r><w:t>{body}</w:t></w:r></w:p></w:body></w:document>')
        sys.path.insert(0, str(ROOT / "review/task-002"))
        from probe_pdf import case_baseline, case_shared_flood_2
        case_baseline(fixtures / "normal.pdf")
        case_shared_flood_2(fixtures / "scaled.pdf")
        for name, kind in (("normal", "docx"), ("scaled", "docx"), ("normal", "pdf"), ("scaled", "pdf")):
            key = name + "_" + kind
            record(key, [sys.executable, str(Path(__file__).resolve()), "worker", str(fixtures / (name + "." + kind)), kind], fixtures, wall=15, cpu=10, memory=512)
        checks["normal_workers"] = all(cases[name]["returncode"] == 0 and json.loads((fixtures / (name + ".out")).read_text())["status"] == "counted" for name in ("normal_docx", "normal_pdf"))
        checks["scaled_docx_bounded"] = json.loads((fixtures / "scaled_docx.out").read_text())["status"] == "too_large"
        checks["scaled_pdf_bounded"] = cases["scaled_pdf"]["returncode"] != 0 or cases["scaled_pdf"]["seconds"] <= 15
        report["passed"] = all(checks.values())
    except Exception as exc:
        report["passed"] = False
        report["failure"] = type(exc).__name__ + ": " + str(exc)
    finally:
        save()
    print(json.dumps({"passed": report["passed"], "checks": checks, "failure": report.get("failure")}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1] == "worker":
        worker(Path(sys.argv[2]), sys.argv[3])
    else:
        main(Path(sys.argv[1]).resolve())
