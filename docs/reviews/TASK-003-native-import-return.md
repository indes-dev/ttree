# TASK-003 amendment 2 — retained final CPU and exhausted native import

Overall **0/4**; native import/containment acceptance remains open. Codex executor,
PROJECT / AGENT, indes-front. No production native adapter/runtime policy was enabled.
No export retrial, new host package, privilege window or persistent service.

## Final kernel accounting

A task-created transient delegated scope contains sibling `meter/` and `reader/`
cgroups. The trusted bounded meter stays outside the reader cgroup. All job
launchers, native processes and escaping descendants enter `reader/`; both siblings
remain below parent memory.max=805306368, swap=0, pids=64, cpu.max=10000 10000.
The reader child has those same caps (128 MiB only for the negative memory control).
No ancestor cgroup was changed. Delegation and settings are only on the new scope.

The supervisor uses reader `cgroup.kill`, waits for kernel `populated=0` and empty
membership, then reads the **retained final cpu.stat** before destroying the scope.
This accounts for the entire reader job through termination, including launchers
and setsid descendants. The trusted sibling meter is not reader work; its bounded
CPU/memory remains under the parent scope caps. This distinction is explicit rather
than claiming a final snapshot for a still-running supervisor.

Live two-process loop: final aggregate CPU **15.011956 s**, final overshoot
**0.011956 s**, within 250 ms. Final populated=0 and no members; scope collected,
reader cgroup removed, all observed PID/starttime identities had no live survivor.
Reduced 128 MiB memory control: memory.peak=134217728; max=26, oom=1, oom_kill=7,
oom_group_kill=1. A setsid child was observed/accounted; the whole reader group was
terminated, counters retained and resources removed. This supersedes the previous
pre-kill-only CPU observation for this diagnostic boundary, subject to Orc review.
It does not accept systemd as a public runtime dependency.

## Direct import

Verified before invocation: public Apache Tika commit
9f9b452634bac9d0e04f78b8c113cd69aee13603,
`tika-parsers/tika-parsers-standard/tika-parsers-standard-modules/tika-parser-microsoft-module/src/test/resources/test-documents/testWORD.doc`.
32768 bytes, OLE signature; Git blob c1f4f3d0b0c1e475bf03e9eba3ed7c7ac166d557;
SHA-256 5ca19b67876f284a0e04ed06df44a004f850629a871fe522d014e1fdff912799.
Reused only the verified Orc scratch copy. No fixture was committed/packaged;
upstream LICENSE/NOTICE remain in `.tmp/orc-fixture-provenance/`.
Expected public text: sample document title and sample Microsoft Word sentence.

Mandatory bubblewrap unshare-all, explicit mounts, private profile/temp/output,
cleared environment and Word 97 import filter were preserved. Reader wall 20 s,
per-process CPU 15 s, aggregate job CPU 15 s. Ordered direct imports:

| Reader AS MiB | Exit | Reader seconds | Final job CPU s | Kernel peak B | OOM kills |
|---:|---:|---:|---:|---:|---:|
| 768 | 139 | 0.7857 | 0.785585 | 68550656 | 0 |
| 1024 | 139 | 0.7978 | 0.787318 | 61435904 | 0 |
| 1536 | 134 | 0.8428 | 0.835982 | 85606400 | 0 |
| 2048 | 139 | 0.8544 | 0.833555 | 74678272 | 0 |

All failed; no expected text/output was observed. The 1024/2048 stderr reported
allocation errors; 1536 reported a deployment/application error; 768 stderr was
empty. Do not infer one root cause or a successful import envelope. No further AS
step or unchanged import/export retry is authorized. Every reader cgroup was empty
before final counters, all six scopes collected, all six private data areas removed.
A final `systemctl --user list-units 'ttree-task003-*' --all --no-legend` was empty.
Real native network/filesystem/PID controls, actual missing/denied boundary calls
and real-reader timeout remain unrun because direct import did not succeed.

## Evidence and continuation

Actual command: `timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0
--fsize=12582912 .venv/bin/python review/task-003/import_diagnostic.py
.tmp/native-import-1` (exit 1: exhausted native import). Batch **20.6219 s**.
`run_import_diagnostic.sh` records the same finite boundary.
`review/task-003/evidence/amendment-2-native/`: compact summary, deterministic
compressed full metric/membership history, exact negative stderr, SHA256SUMS.
Source-start HEAD 02012e7; the script digest is preserved with summary.

Native stream now returns to Orc for adjudication. Independent base semantics,
dependency/artifact/matrix work continues under amendment 2. DOC stays explicitly
unsupported with null tokens/incomplete results. No finding closure, phase-1
acceptance, independent reviewer dispatch, installed CLI change or release action.
