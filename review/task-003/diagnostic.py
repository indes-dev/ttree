"""TASK-003 amendment-1 diagnostic. Trusted supervisor stays outside each scope.

Synthetic inputs only. Nothing here changes production limits or dependencies.
Run with run_diagnostic.sh; the outer trusted batch also has finite limits.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from prototype import MIB, OLE, ROOT, fresh, limits, reader, sandbox

SCRIPT = Path(__file__).resolve()
POLL = 0.02
CONTROLS = ("memory.max", "memory.swap.max", "pids.max", "cpu.max")
METRICS = ("memory.current", "memory.peak", "memory.events", "cpu.stat", "pids.current", "pids.events", "cgroup.events")


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(".writing")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def values(path: Path) -> dict:
    result = {}
    for name in (*CONTROLS, *METRICS):
        try:
            raw = (path / name).read_text().strip()
            result[name] = dict(line.split() for line in raw.splitlines()) if " " in raw and name != "cpu.max" else raw
        except OSError:
            result[name] = None
    return result


def membership(path: Path) -> list[dict]:
    result = []
    try:
        pids = (path / "cgroup.procs").read_text().split()
    except OSError:
        return result
    for pid in pids:
        proc = Path("/proc") / pid
        try:
            stat = (proc / "stat").read_text().rsplit(")", 1)[1].split()
            status = (proc / "status").read_text().splitlines()
            result.append({"pid": int(pid), "starttime": stat[19], "session": int(stat[3]),
                           "cgroup": (proc / "cgroup").read_text().strip(),
                           "nspid": next((line for line in status if line.startswith("NSpid:")), None)})
        except OSError:
            pass
    return result


def launch(work: Path) -> None:
    """Trusted pre-reader child. Its control files are never mounted to the reader."""
    spec = json.loads((work / "spec.json").read_text())
    cg = Path("/sys/fs/cgroup" + Path("/proc/self/cgroup").read_text().strip().split("::", 1)[1])
    write_json(work / "ready.json", {"cgroup": str(cg), "pid": os.getpid(), "limits": values(cg)})
    deadline = time.monotonic() + 21
    while not (work / "go").exists():
        if time.monotonic() >= deadline:
            raise SystemExit(2)
        time.sleep(.005)
    # Bring up loopback only inside the per-job disposable network namespace.
    subprocess.run(["/usr/bin/ip", "link", "set", "lo", "up"], check=True, timeout=1)
    start = time.monotonic()
    result = {"status": "failed"}
    try:
        with (work / "stdout").open("wb") as out, (work / "stderr").open("wb") as err:
            process = subprocess.Popen(spec["command"], stdout=out, stderr=err,
                                       env={"PATH": "/usr/bin", "LANG": "C.UTF-8"},
                                       preexec_fn=lambda: limits(spec["as_mib"], spec["cpu_seconds"]))
            code = process.wait()
            result = {"returncode": code, "status": "ok" if code == 0 else "failed"}
    except FileNotFoundError:
        result = {"returncode": None, "status": "sandbox_unavailable"}
    finally:
        result["seconds"] = round(time.monotonic() - start, 4)
        write_json(work / "done.json", result)
    # Hold counters until the external supervisor records and kills the whole scope.
    while time.monotonic() < deadline:
        time.sleep(.02)


class Supervisor:
    def __init__(self, root: Path):
        self.root = root
        self.started = time.monotonic()
        self.deadline = self.started + 115
        self.report = {"starting_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                       "batch_wall_seconds": 115, "batch_cpu_seconds_per_process": 60,
                       "poll_seconds": POLL, "cases": {}, "checks": {}, "passed": False}
        self.root.mkdir(parents=True, exist_ok=False)

    def save(self):
        self.report["elapsed_seconds"] = round(time.monotonic() - self.started, 4)
        write_json(self.root / "results.json", self.report)

    def check(self, name: str, okay: bool):
        self.report["checks"][name] = bool(okay)
        self.save()
        if not okay:
            raise RuntimeError(name + " failed; stop under frozen amendment")

    def run(self, name: str, command: list[str], work: Path, *, as_mib=512, memory_mib=768,
            wall=20, cpu_seconds=15, aggregate_cpu=15) -> dict:
        if time.monotonic() >= self.deadline - 2:
            raise RuntimeError("batch deadline exhausted")
        work.mkdir(parents=True, exist_ok=True)
        unit = "ttree-task003-" + uuid.uuid4().hex[:12] + ".scope"
        spec = {"command": command, "as_mib": as_mib, "cpu_seconds": cpu_seconds}
        write_json(work / "spec.json", spec)
        args = ["/usr/bin/systemd-run", "--user", "--scope", "--quiet", "--collect", "--unit=" + unit,
                "--property=MemoryMax=" + str(memory_mib * MIB), "--property=MemorySwapMax=0",
                "--property=TasksMax=64", "--property=CPUQuota=100%", "--property=CPUQuotaPeriodSec=10ms",
                "--property=RuntimeMaxSec=22s", "--property=TimeoutStopSec=100ms", "--property=KillMode=control-group",
                "/usr/bin/prlimit", "--as=2147483648", "--cpu=60", "--core=0",
                "/usr/bin/unshare", "-Urnpf", "--mount-proc", sys.executable, str(SCRIPT), "launch", str(work)]
        result = {"scope": unit, "command": command, "scope_command": args,
                  "as_mib_per_reader_process": as_mib, "wall_seconds": wall,
                  "cpu_seconds_per_reader_process": cpu_seconds, "aggregate_cpu_limit_seconds": aggregate_cpu,
                  "metrics_samples": [], "membership_samples": [], "status": "startup_failed"}
        self.report["cases"][name] = result
        cg = None
        child = None
        identities = {}
        start = time.monotonic()
        peak_rss = peak_vms = 0
        try:
            with (work / "scope.stdout").open("wb") as out, (work / "scope.stderr").open("wb") as err:
                child = subprocess.Popen(args, stdout=out, stderr=err,
                                         env={"PATH": "/usr/bin", "LANG": "C.UTF-8",
                                              "XDG_RUNTIME_DIR": "/run/user/" + str(os.getuid())})
            while not (work / "ready.json").exists():
                if child.poll() is not None or time.monotonic() - start > 3:
                    raise RuntimeError("dedicated cgroup startup failed")
                time.sleep(.01)
            ready = json.loads((work / "ready.json").read_text())
            cg = Path(ready["cgroup"])
            if cg.name != unit or not str(cg).startswith("/sys/fs/cgroup/user.slice/"):
                raise RuntimeError("unexpected cgroup identity")
            initial = values(cg)
            expected = {"memory.max": str(memory_mib * MIB), "memory.swap.max": "0", "pids.max": "64", "cpu.max": "10000 10000"}
            if any(initial.get(key) != value for key, value in expected.items()):
                raise RuntimeError("kernel cgroup readback mismatch")
            result["initial"] = initial
            result["readback_before_reader"] = True
            result["supervisor_cgroup"] = Path("/proc/self/cgroup").read_text().strip()
            if unit in result["supervisor_cgroup"]:
                raise RuntimeError("supervisor entered reader cgroup")
            (work / "go").touch()
            reader_start = time.monotonic()
            while True:
                snapshot = values(cg)
                members = membership(cg)
                sample_time = round(time.monotonic() - reader_start, 4)
                result["metrics_samples"].append({"seconds": sample_time, **snapshot})
                if members and (len(result["membership_samples"]) < 4 or (work / "data/child.json").exists()):
                    if len(result["membership_samples"]) < 20:
                        result["membership_samples"].append({"seconds": sample_time, "members": members})
                for member in members:
                    identities[member["pid"]] = member["starttime"]
                process_values = []
                for member in members:
                    try:
                        process_values.append([int(n) * os.sysconf("SC_PAGE_SIZE") // 1024 for n in (Path("/proc") / str(member["pid"]) / "statm").read_text().split()[:2]])
                    except OSError:
                        pass
                peak_rss = max(peak_rss, sum(v[1] for v in process_values))
                peak_vms = max(peak_vms, max((v[0] for v in process_values), default=0))
                used = int((snapshot.get("cpu.stat") or {}).get("usage_usec", "0")) / 1_000_000
                oom = int((snapshot.get("memory.events") or {}).get("oom_kill", "0"))
                if oom:
                    result["status"] = "oom_killed"
                    break
                if used >= aggregate_cpu:
                    result["status"] = "cpu_limit"
                    result["cpu_overshoot_seconds"] = round(used - aggregate_cpu, 6)
                    break
                if time.monotonic() - reader_start >= wall or time.monotonic() >= self.deadline - 1:
                    result["status"] = "timed_out"
                    break
                if (work / "done.json").exists():
                    result["reader_result"] = json.loads((work / "done.json").read_text())
                    result["status"] = result["reader_result"]["status"]
                    break
                if child.poll() is not None:
                    result["status"] = "scope_failed"
                    break
                time.sleep(POLL)
            result["final_before_kill"] = values(cg)
            result["final_membership"] = membership(cg)
            if (work / "data/child.json").exists():
                result["child_marker"] = json.loads((work / "data/child.json").read_text())
        finally:
            # No process-group-only cleanup. The manager kills every scope member.
            if child is not None:
                result["kill_returncode"] = subprocess.run(["/usr/bin/systemctl", "--user", "kill", "--kill-whom=all", "--signal=KILL", unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2).returncode
                subprocess.run(["/usr/bin/systemctl", "--user", "stop", unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                result["unit_inactive"] = subprocess.run(["/usr/bin/systemctl", "--user", "is-active", "--quiet", unit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2).returncode != 0
                result["scope_collected"] = subprocess.run(["/usr/bin/systemctl", "--user", "show", "--property=LoadState", "--value", unit], capture_output=True, text=True, timeout=2).stdout.strip() == "not-found"
            result["survivors"] = []
            for pid, birth in identities.items():
                try:
                    stat = (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
                    if stat[19] == birth and stat[0] != "Z":
                        result["survivors"].append(pid)
                except OSError:
                    pass
            result["cgroup_empty_or_removed"] = cg is not None and (not cg.exists() or not membership(cg))
            result["sampled_peak_tree_rss_kib"] = peak_rss
            result["sampled_peak_process_vms_kib"] = peak_vms
            result["total_seconds"] = round(time.monotonic() - start, 4)
            self.save()
        self.check(name + "_cleanup", result["unit_inactive"] and result["scope_collected"] and not result["survivors"] and result["cgroup_empty_or_removed"])
        return result


def prepare(root: Path, name: str) -> tuple[Path, Path]:
    work = root / name
    return work, fresh(work, "data")


def cleanup_data(supervisor: Supervisor, name: str, data: Path) -> None:
    # Only our own synthetic private work directory, under the approved scratch root.
    shutil.rmtree(data)
    supervisor.check(name + "_private_outputs_removed", not data.exists())


def main(root: Path, mode: str) -> None:
    sup = Supervisor(root)
    try:
        sup.report["versions"] = {"python": sys.version, "kernel": os.uname().release,
            "systemd": subprocess.check_output(["systemd-run", "--version"], text=True).splitlines()[0],
            "bubblewrap": subprocess.check_output(["bwrap", "--version"], text=True).strip(),
            "libreoffice": subprocess.check_output(["libreoffice", "--version"], text=True).strip()}
        if mode == "enforcement":
            work, data = prepare(root, "memory")
            # A bounded 192 MiB child exceeds the reduced 128 MiB aggregate ceiling.
            # The setsid child writes its namespace PID before touching allocations.
            script = ("import os,time,json; from pathlib import Path; p=os.fork(); "
                "\nif p==0:\n os.setsid(); Path('/work/child.json').write_text(json.dumps({'pid':os.getpid(),'sid':os.getsid(0)})); time.sleep(.15); a=[]\n for i in range(192): a.append(bytearray(1024*1024)); time.sleep(.002)\n time.sleep(3)\n"
                "else: time.sleep(5)\n")
            result = sup.run("memory", sandbox(data, ["/usr/bin/python3.14", "-c", script]), work, memory_mib=128, wall=6, cpu_seconds=5)
            sup.check("memory_kernel_enforced", result["status"] == "oom_killed" and int(result["final_before_kill"]["memory.events"]["oom_kill"]) > 0)
            marker = result.get("child_marker", {})
            matched = any(str(marker.get("pid")) == (m.get("nspid") or "").split()[-1] for sample in result["membership_samples"] for m in sample["members"])
            sup.check("escaped_child_accounted", marker.get("pid") == marker.get("sid") and bool(marker) and matched)
            cleanup_data(sup, "memory", data)

            work, data = prepare(root, "cpu")
            script = "import os; p=os.fork(); os.setsid() if p==0 else None\nwhile True: pass\n"
            result = sup.run("cpu", sandbox(data, ["/usr/bin/python3.14", "-c", script]), work, wall=20)
            sup.check("aggregate_cpu_enforced", result["status"] == "cpu_limit" and result.get("cpu_overshoot_seconds", 1) <= .25)
            cleanup_data(sup, "cpu", data)
        elif mode == "doc":
            # The preceding enforcement batch must have succeeded. It is evidence,
            # not merely a property readback; do not bypass it by running doc alone.
            proof = json.loads((root.parent / "diagnostic-enforcement/results.json").read_text())
            if not proof["passed"]:
                raise RuntimeError("aggregate enforcement prerequisite not met")
            fixture = None
            for as_mib in (1024, 1536, 2048):
                name = "export_" + str(as_mib)
                work, data = prepare(root, name)
                (data / "source.txt").write_text("Synthetic legacy Word document text for TASK-003 diagnostic.\n")
                result = sup.run(name, reader(data, "/work/source.txt", "doc:MS Word 97"), work, as_mib=as_mib)
                output = data / "output/source.doc"
                okay = result["status"] == "ok" and output.exists() and output.read_bytes()[:8] == OLE
                result["ole_export_observed"] = okay
                if okay:
                    fixture = root / "synthetic.doc"
                    shutil.copyfile(output, fixture)
                    sup.report["fixture"] = {"path": str(fixture), "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(), "bytes": fixture.stat().st_size, "export_as_mib": as_mib}
                cleanup_data(sup, name, data)
                if okay:
                    break
            sup.check("native_export", fixture is not None)
            for as_mib in (768, 1024, 1536, 2048):
                name = "import_" + str(as_mib)
                work, data = prepare(root, name)
                (data / "input.doc").write_bytes(fixture.read_bytes())
                # Private fixed profile is defense in depth, not containment proof.
                (data / "profile/user/registrymodifications.xcu").write_text(
                    '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
                    '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
                    '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop>'
                    '<prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop>'
                    '<prop oor:name="DisableActiveContent" oor:op="fuse"><value>true</value></prop></item>'
                    '<item oor:path="/org.openoffice.Office.Writer/Content/Update">'
                    '<prop oor:name="Link" oor:op="fuse"><value>2</value></prop>'
                    '<prop oor:name="Field" oor:op="fuse"><value>false</value></prop></item></oor:items>')
                sup.check(name + "_signature", (data / "input.doc").read_bytes()[:8] == OLE)
                result = sup.run(name, reader(data, "/work/input.doc", "txt:Text (encoded):UTF8", word_filter=True), work, as_mib=as_mib)
                output = data / "output/input.txt"
                okay = result["status"] == "ok" and output.exists() and "Synthetic legacy Word document text" in output.read_text(encoding="utf-8-sig")
                result["native_import_text_observed"] = okay
                if okay:
                    sup.report["import_as_mib"] = as_mib
                cleanup_data(sup, name, data)
                if okay:
                    break
            sup.check("native_import", "import_as_mib" in sup.report)
        else:
            raise ValueError("unknown diagnostic mode")
        sup.report["passed"] = True
    except Exception as exc:
        sup.report["failure"] = type(exc).__name__ + ": " + str(exc)
    finally:
        sup.save()
    print(json.dumps({"passed": sup.report["passed"], "checks": sup.report["checks"], "failure": sup.report.get("failure"), "elapsed_seconds": sup.report["elapsed_seconds"]}))
    if not sup.report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    if sys.argv[1] == "launch":
        launch(Path(sys.argv[2]))
    else:
        main(Path(sys.argv[1]).resolve(), sys.argv[2])
