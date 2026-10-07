"""Amendment 2 native import diagnostic; retained empty reader cgroup counters.

A bounded trusted meter lives in a sibling cgroup. Every reader job process,
including launchers and setsid descendants, lives in reader/. Kill that entire
cgroup, confirm populated=0, THEN read cpu.stat before removing the scope.
The meter is excluded from reader accounting; both remain under parent caps.
No ancestor settings or production runtime dependency changes.
"""

from __future__ import annotations
import hashlib, json, os, resource, shutil, subprocess, sys, time, uuid
from pathlib import Path
from diagnostic import values, membership, write_json
from prototype import MIB, OLE, ROOT, fresh, limits, reader, sandbox

SCRIPT = Path(__file__).resolve()
EXPECTED_SHA = "5ca19b67876f284a0e04ed06df44a004f850629a871fe522d014e1fdff912799"
EXPECTED_BLOB = "c1f4f3d0b0c1e475bf03e9eba3ed7c7ac166d557"


def keeper(work):
    spec = json.loads((work / "spec.json").read_text())
    parent = Path(
        "/sys/fs/cgroup" + Path("/proc/self/cgroup").read_text().strip().split("::")[1]
    )
    (parent / "meter").mkdir()
    job = parent / "reader"
    job.mkdir()
    (parent / "meter/cgroup.procs").write_text(str(os.getpid()))
    (parent / "cgroup.subtree_control").write_text("+cpu +memory +pids")
    for name, value in {
        "memory.max": str(spec["memory_mib"] * MIB),
        "memory.swap.max": "0",
        "pids.max": "64",
        "cpu.max": "10000 10000",
        "memory.oom.group": "1",
    }.items():
        (job / name).write_text(value)
    write_json(
        work / "ready.json",
        {
            "reader_cgroup": str(job),
            "scope_cgroup": str(parent),
            "reader_limits": values(job),
            "scope_limits": values(parent),
        },
    )
    deadline = time.monotonic() + 24
    while not (work / "go").exists():
        if time.monotonic() > deadline:
            raise SystemExit(2)
        time.sleep(0.005)

    def enter():
        (job / "cgroup.procs").write_text(str(os.getpid()))

    with (
        (work / "launch.stdout").open("wb") as out,
        (work / "launch.stderr").open("wb") as err,
    ):
        process = subprocess.Popen(
            [
                "/usr/bin/unshare",
                "-Urnpf",
                "--mount-proc",
                sys.executable,
                str(SCRIPT),
                "job",
                str(work),
            ],
            preexec_fn=enter,
            stdout=out,
            stderr=err,
        )
        while time.monotonic() < deadline:
            time.sleep(0.01)
        process.wait(timeout=0.2)


def job(work):
    spec = json.loads((work / "spec.json").read_text())
    subprocess.run(["/usr/bin/ip", "link", "set", "lo", "up"], check=True, timeout=1)
    start = time.monotonic()
    with (work / "stdout").open("wb") as out, (work / "stderr").open("wb") as err:
        process = subprocess.Popen(
            spec["command"],
            stdout=out,
            stderr=err,
            env={"PATH": "/usr/bin", "LANG": "C.UTF-8"},
            preexec_fn=lambda: limits(spec["as_mib"], spec["cpu_seconds"]),
        )
        code = process.wait()
    write_json(
        work / "done.json",
        {"returncode": code, "seconds": round(time.monotonic() - start, 4)},
    )


class Supervisor:
    def __init__(self, root):
        root.mkdir(parents=True, exist_ok=False)
        self.root = root
        self.start = time.monotonic()
        self.deadline = self.start + 115
        self.report = {
            "starting_head": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "scope": "transient delegated scope with retained reader cgroup; no production changes",
            "batch_wall_seconds": 115,
            "poll_seconds": 0.02,
            "cases": {},
            "checks": {},
            "passed": False,
        }

    def save(self):
        self.report["elapsed_seconds"] = round(time.monotonic() - self.start, 4)
        write_json(self.root / "results.json", self.report)

    def check(self, name, value):
        self.report["checks"][name] = bool(value)
        self.save()
        if not value:
            raise RuntimeError(name + " failed")

    def run(
        self, name, command, *, as_mib=512, memory_mib=768, wall=20, cpu_seconds=15
    ):
        if time.monotonic() > self.deadline - wall - 3:
            raise RuntimeError("remaining batch budget insufficient")
        work = self.root / name
        work.mkdir(exist_ok=True)
        spec = {
            "command": command,
            "as_mib": as_mib,
            "memory_mib": memory_mib,
            "cpu_seconds": cpu_seconds,
        }
        write_json(work / "spec.json", spec)
        unit = "ttree-task003-import-" + uuid.uuid4().hex[:12] + ".scope"
        args = [
            "systemd-run",
            "--user",
            "--scope",
            "--quiet",
            "--collect",
            "--unit=" + unit,
            "-p",
            "Delegate=yes",
            "-p",
            "MemoryMax=" + str(768 * MIB),
            "-p",
            "MemorySwapMax=0",
            "-p",
            "TasksMax=64",
            "-p",
            "CPUQuota=100%",
            "-p",
            "CPUQuotaPeriodSec=10ms",
            "-p",
            "RuntimeMaxSec=25s",
            "-p",
            "TimeoutStopSec=100ms",
            "-p",
            "KillMode=control-group",
            sys.executable,
            str(SCRIPT),
            "keeper",
            str(work),
        ]
        result = {
            "scope": unit,
            "command": command,
            "scope_command": args,
            "as_mib_per_reader_process": as_mib,
            "reader_wall_seconds": wall,
            "aggregate_cpu_seconds": 15,
            "cpu_seconds_per_reader_process": cpu_seconds,
            "memory_mib_aggregate_reader": memory_mib,
            "samples": [],
            "status": "startup_failed",
        }
        self.report["cases"][name] = result
        cg = None
        process = None
        identities = {}
        started = time.monotonic()
        try:
            with (
                (work / "scope.stdout").open("wb") as out,
                (work / "scope.stderr").open("wb") as err,
            ):
                process = subprocess.Popen(args, stdout=out, stderr=err)
            while not (work / "ready.json").exists():
                if process.poll() is not None or time.monotonic() - started > 3:
                    raise RuntimeError("delegated cgroup startup unavailable")
                time.sleep(0.005)
            ready = json.loads((work / "ready.json").read_text())
            cg = Path(ready["reader_cgroup"])
            parent = Path(ready["scope_cgroup"])
            self.check(
                name + "_identity",
                parent.name == unit
                and cg == parent / "reader"
                and unit not in Path("/proc/self/cgroup").read_text(),
            )
            required = {
                "memory.max": str(memory_mib * MIB),
                "memory.swap.max": "0",
                "pids.max": "64",
                "cpu.max": "10000 10000",
            }
            self.check(
                name + "_kernel_readback",
                all(ready["reader_limits"][k] == v for k, v in required.items()),
            )
            result["readback"] = ready
            (work / "go").touch()
            reader_start = time.monotonic()
            while True:
                metric = values(cg)
                members = membership(cg)
                for member in members:
                    identities[member["pid"]] = member["starttime"]
                sample = {
                    "seconds": round(time.monotonic() - reader_start, 4),
                    "metrics": metric,
                    "members": members,
                }
                result["samples"].append(sample)
                used = int((metric["cpu.stat"] or {}).get("usage_usec", 0)) / 1e6
                if int((metric["memory.events"] or {}).get("oom_kill", 0)):
                    result["status"] = "oom_killed"
                    break
                if used >= 15:
                    result["status"] = "cpu_limit"
                    result["trigger_cpu_seconds"] = used
                    break
                if (
                    time.monotonic() - reader_start >= wall
                    or time.monotonic() >= self.deadline - 2
                ):
                    result["status"] = "timed_out"
                    break
                if (work / "done.json").exists():
                    result["reader_result"] = json.loads(
                        (work / "done.json").read_text()
                    )
                    result["status"] = (
                        "ok" if result["reader_result"]["returncode"] == 0 else "failed"
                    )
                    break
                if process.poll() is not None:
                    raise RuntimeError("scope ended before retained accounting")
                time.sleep(0.02)
            result["before_termination"] = values(cg)
            # cgroup.kill targets all processes in this reader subtree, regardless
            # of parent/session/PID namespaces. Meter remains outside that subtree.
            (cg / "cgroup.kill").write_text("1")
            end = time.monotonic() + 2
            while (
                time.monotonic() < end
                and (values(cg)["cgroup.events"] or {}).get("populated") != "0"
            ):
                time.sleep(0.005)
            result["final_after_whole_tree_termination"] = values(cg)
            result["final_members"] = membership(cg)
            final = result["final_after_whole_tree_termination"]
            result["final_cpu_seconds"] = (
                int((final["cpu.stat"] or {}).get("usage_usec", 0)) / 1e6
            )
            result["final_cpu_overshoot_seconds"] = max(
                0, round(result["final_cpu_seconds"] - 15, 6)
            )
            self.check(
                name + "_retained_final_accounting",
                final["cpu.stat"] is not None
                and final["cgroup.events"]["populated"] == "0"
                and not result["final_members"],
            )
            self.check(
                name + "_cpu_final_overshoot",
                result["final_cpu_overshoot_seconds"] <= 0.25,
            )
            if (work / "data/child.json").exists():
                result["child_marker"] = json.loads(
                    (work / "data/child.json").read_text()
                )
        finally:
            if process is not None:
                subprocess.run(
                    [
                        "systemctl",
                        "--user",
                        "kill",
                        "--kill-whom=all",
                        "--signal=KILL",
                        unit,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                subprocess.run(
                    ["systemctl", "--user", "stop", unit],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2,
                )
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                result["scope_collected"] = (
                    subprocess.run(
                        [
                            "systemctl",
                            "--user",
                            "show",
                            "--property=LoadState",
                            "--value",
                            unit,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    ).stdout.strip()
                    == "not-found"
                )
            result["survivors"] = []
            for pid, birth in identities.items():
                try:
                    fields = (
                        (Path("/proc") / str(pid) / "stat")
                        .read_text()
                        .rsplit(")", 1)[1]
                        .split()
                    )
                    if fields[19] == birth and fields[0] != "Z":
                        result["survivors"].append(pid)
                except OSError:
                    pass
            result["reader_cgroup_removed"] = cg is not None and not cg.exists()
            result["total_seconds"] = round(time.monotonic() - started, 4)
            self.save()
        self.check(
            name + "_cleanup",
            result.get("scope_collected", False)
            and result["reader_cgroup_removed"]
            and not result["survivors"],
        )
        return result


def main(root):
    supervisor = Supervisor(root)
    try:
        fixture = ROOT / ".tmp/orc-fixture-provenance/testWORD.doc"
        raw = fixture.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        supervisor.check(
            "pinned_fixture",
            len(raw) == 32768
            and raw[:8] == OLE
            and hashlib.sha256(raw).hexdigest() == EXPECTED_SHA
            and blob == EXPECTED_BLOB,
        )
        supervisor.report["fixture"] = {
            "commit": "9f9b452634bac9d0e04f78b8c113cd69aee13603",
            "git_blob": blob,
            "bytes": len(raw),
            "sha256": EXPECTED_SHA,
            "upstream_path": "tika-parsers/tika-parsers-standard/tika-parsers-standard-modules/tika-parser-microsoft-module/src/test/resources/test-documents/testWORD.doc",
            "expected_text": [
                "Sample Word Document Title",
                "This is a sample Microsoft Word Document.",
            ],
            "fixture_not_committed": True,
            "license_notice_verified_scratch": ".tmp/orc-fixture-provenance/",
        }
        name = "memory"
        data = fresh(root / name, "data")
        script = "import os,time,json; from pathlib import Path; p=os.fork()\nif p==0:\n os.setsid(); Path('/work/child.json').write_text(json.dumps({'pid':os.getpid(),'sid':os.getsid(0)})); time.sleep(.1); a=[]\n for i in range(192):a.append(bytearray(1024*1024));time.sleep(.002)\n time.sleep(5)\nelse:time.sleep(5)"
        result = supervisor.run(
            name,
            sandbox(data, ["/usr/bin/python3.14", "-c", script]),
            memory_mib=128,
            wall=6,
        )
        supervisor.check(
            "memory_kernel_enforcement",
            result["status"] == "oom_killed"
            and int(
                result["final_after_whole_tree_termination"]["memory.events"][
                    "oom_kill"
                ]
            )
            > 0,
        )
        marker = result.get("child_marker", {})
        matched = any(
            str(marker.get("pid")) == (m.get("nspid") or "").split()[-1]
            for s in result["samples"]
            for m in s["members"]
        )
        supervisor.check(
            "setsid_accounted",
            bool(marker) and marker.get("pid") == marker.get("sid") and matched,
        )
        shutil.rmtree(data)
        name = "cpu"
        data = fresh(root / name, "data")
        result = supervisor.run(
            name,
            sandbox(
                data,
                [
                    "/usr/bin/python3.14",
                    "-c",
                    "import os; p=os.fork(); os.setsid() if p==0 else None\nwhile True:pass",
                ],
            ),
            wall=20,
        )
        supervisor.check(
            "final_aggregate_cpu_enforced",
            result["status"] == "cpu_limit"
            and result["final_cpu_overshoot_seconds"] <= 0.25,
        )
        shutil.rmtree(data)
        success = False
        for as_mib in (768, 1024, 1536, 2048):
            name = "import_" + str(as_mib)
            data = fresh(root / name, "data")
            (data / "input.doc").write_bytes(raw)
            (data / "profile/user/registrymodifications.xcu").write_text(
                '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry"><item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop><prop oor:name="DisableMacrosExecution" oor:op="fuse"><value>true</value></prop><prop oor:name="DisableActiveContent" oor:op="fuse"><value>true</value></prop></item><item oor:path="/org.openoffice.Office.Writer/Content/Update"><prop oor:name="Link" oor:op="fuse"><value>2</value></prop><prop oor:name="Field" oor:op="fuse"><value>false</value></prop></item></oor:items>'
            )
            result = supervisor.run(
                name,
                reader(
                    data, "/work/input.doc", "txt:Text (encoded):UTF8", word_filter=True
                ),
                as_mib=as_mib,
            )
            output = data / "output/input.txt"
            observed = output.read_text(encoding="utf-8-sig") if output.exists() else ""
            success = result["status"] == "ok" and all(
                text in observed
                for text in supervisor.report["fixture"]["expected_text"]
            )
            result["expected_text_observed"] = success
            if success:
                supervisor.report["import_as_mib"] = as_mib
            result["output_bytes"] = output.stat().st_size if output.exists() else None
            result["output_sha256"] = (
                hashlib.sha256(output.read_bytes()).hexdigest()
                if output.exists()
                else None
            )
            shutil.rmtree(data)
            supervisor.check(name + "_private_data_removed", not data.exists())
            if success:
                break
        supervisor.report["native_import_success"] = success
        # Parent live native controls are a separate finite follow-up on success.
        supervisor.report["native_controls_complete"] = False
        supervisor.report["passed"] = (
            all(supervisor.report["checks"].values()) and success
        )
        if not success:
            supervisor.report["failure"] = "finite native import ceilings exhausted"
    except Exception as exc:
        supervisor.report["failure"] = type(exc).__name__ + ": " + str(exc)
    finally:
        supervisor.save()
    print(
        json.dumps(
            {
                "checks": supervisor.report["checks"],
                "native_import_success": supervisor.report.get("native_import_success"),
                "failure": supervisor.report.get("failure"),
                "seconds": supervisor.report["elapsed_seconds"],
            }
        )
    )
    return 0 if supervisor.report["passed"] else 1


if __name__ == "__main__":
    if sys.argv[1] == "keeper":
        keeper(Path(sys.argv[2]))
    elif sys.argv[1] == "job":
        job(Path(sys.argv[2]))
    else:
        raise SystemExit(main(Path(sys.argv[1]).resolve()))
