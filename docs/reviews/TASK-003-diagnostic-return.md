# TASK-003 amendment 1: diagnostic return

Date: 2026-10-07 UTC. Executor: Codex, PROJECT / AGENT, indes-front.
Starting HEAD: `f87e6493cb9a3234b9b1cf6054621a7b949ca8a0`.
Authority: unchanged TASK-003 plus its frozen diagnostic amendment at that SHA.
Result: failed native export at every authorized AS trial, including 2048 MiB.
Return to ttree Orc. Phase 1 remains incomplete, 0/4; phase 2 did not start.

## Concrete outcome

Aggregate cgroup memory enforcement and escaping-session cleanup were exercised
with synthetic processes. A separate native-reader batch then attempted to export
one short synthetic text file to Word 97 DOC at 1024, 1536 and 2048 MiB AS.
Every attempt failed with `std::bad_alloc`. No OLE fixture was produced, so actual
DOC import and the subsequent live native-reader/worker controls could not run.
The amendment's finite upper-ceiling stop applies. No usable import envelope can
be proposed from this evidence.

This failure narrows the earlier hypothesis: increasing AS to the authorized
2 GiB diagnostic ceiling did not establish feasibility. It does not prove that
any larger envelope or a different runtime would work. Neither was tested.

## Preflight and exact batches

Host: indes-front, Arch Linux, kernel 7.2.8-arch1-2. Python 3.12.14,
LibreOffice 26.8.0.3 680(Build:3), bubblewrap 0.13.0, systemd 262 (262-1-arch).
Observed available memory was 17,330 MiB. The source branch and remote matched
f87e649; worktree was clean and PR #1 OPEN/DRAFT before edits. Production files
still matched the reviewed 9d420db baseline.

Commands, run from `/home/zak/projects/ttree`:

```bash
bash review/task-003/run_diagnostic.sh .tmp/diagnostic-enforcement enforcement
bash review/task-003/run_diagnostic.sh .tmp/diagnostic-doc doc
```

Each trusted batch had a 115 s wall deadline, 60 s per-process CPU limit and
2048 MiB finite AS ceiling. Observed batch elapsed times were 15.7753 s and
3.3999 s, respectively, 19.1752 s cumulative. No native experiment followed the
failed 2048 MiB trial.

Each job used its own authorized transient user-systemd scope. The supervisor
remained outside it. A trusted child held the reader until the supervisor read
the kernel controls; control files were outside the reader's mounted work area.
The child then created a disposable user/network/PID/mount namespace and invoked
the mandatory bubblewrap boundary. `/usr` runtime and required distribution
font/bootstrap configuration were read-only; home, profile, output and temp were
private. Reader environment was cleared. No host user-manager bus, host home,
control files or cgroup mount was exposed to the reader.

Kernel readback before each reader: memory.swap.max=0, pids.max=64,
cpu.max=`10000 10000` (one CPU, 10 ms quota period). MemoryMax was 128 MiB for the
small memory test and 768 MiB for CPU/native tests. Native jobs inherited the
selected soft/hard AS and 15 s per-process CPU limits, 12 MiB output-file limits
and disabled core dumps. A supervisor wall limit of 20 s was supplemented by a
22 s scope lifetime and 100 ms stop timeout. All controls affect only task-created
transient units; no ancestor cgroup or persistent setting was changed.

## Live aggregate controls

The bounded memory fixture forked a child which called setsid, wrote its namespace
PID/session marker, and touched at most 192 MiB in small increments. The external
supervisor matched its namespace PID to the dedicated scope's actual members.
The reduced 128 MiB group reached memory.peak=134217728, memory.events:max=29,
oom=1, oom_kill=1. The supervisor observed the OOM and killed the entire scope.
No survivor remained, the group was empty/removed, the scope was collected, and
the task's private data/profile/temp/output directory was removed.

A separate two-process CPU loop included a setsid child. Both stayed in the quota
group. At the 15 s aggregate CPU threshold the supervisor initiated whole-scope
cleanup. Poll interval: 20 ms. Trigger snapshot usage: 15.008150 s; the final
pre-kill snapshot was 15.012145 s. cpu.stat reported 1500 throttled periods.
Both transient scope and descendants were removed; the private work area was
removed. This establishes an aggregate CPU abort and quota enforcement observation.

Limitation: the cgroup was collected after the kill, so no final post-termination
cpu.stat was retained. The 8.150 ms trigger overshoot and 12.145 ms pre-kill
overshoot are measured; complete termination overshoot is unverified. The local
script's `aggregate_cpu_enforced` assertion checks the trigger snapshot only.
Its internal `passed=true` must not be read as full amendment acceptance or proof
of the required final <=250 ms termination overshoot. Improve this accounting
before any eventual full boundary acceptance.

## Distinct native export results

All native scopes had memory.max=805306368, swap 0, 64 tasks and one CPU quota.
All three reader diagnostics were allocation failures; none had a kernel OOM kill.

| Export AS | Native elapsed | Reader exit | Kernel memory.peak | Aggregate CPU at final pre-kill snapshot | Sampled maximum process virtual size |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1024 MiB | 0.8447 s | 139 | 61,394,944 B | 0.832150 s | 1,048,576 KiB |
| 1536 MiB | 1.2304 s | 134 | 180,699,136 B | 0.915567 s | 1,572,852 KiB |
| 2048 MiB | 0.9082 s | 134 | 74,399,744 B | 0.887733 s | 2,097,152 KiB |

The trusted job launcher and reader descendants were sampled in their dedicated
scope. The maximum virtual sizes reached or approached the trial ceiling.
These observations support continuing to investigate virtual mappings/allocation,
but do not establish a root cause. Group charged memory stayed below 768 MiB with
zero OOM events. It is not interchangeable with summed process RSS or virtual size.
Sampled tree RSS was 202032/310004/302204 KiB; it can double-count shared pages.
Sampling may miss short peaks. No wrapper wait4 metric is used as tree accounting.

After every failed export, whole-scope termination was observed, recorded process
identities had no live survivors, the cgroup was empty/removed, the scope was
collected and its private data/profile/temp/output directory was removed. A final
user-manager query found no loaded `ttree-task003-*` units. Core dumps were disabled.

## Evidence and unrun checks

Public evidence is under `review/task-003/evidence/amendment-1/`:
summary JSON contains exact commands, limits, initial/final counters, namespace
membership, statuses and cleanup. Deterministic gzip files retain the full raw
metric/membership histories; no prior raw result was rewritten. Export stderr
files retain the synthetic allocation diagnostics. SHA256SUMS covers these files.
Local scratch and exact scope stdout/stderr remain in the checkpoint's paths.

No native DOC fixture, provenance digest or import count exists. Native import at
768/1024/1536/2048 MiB is unrun. Real-reader network/filesystem positive/denial
controls, denied/missing namespace invocation, native timeout, bounded workers and
oversized IPC are unrun. The synthetic setsid/OOM/CPU observations do not replace
those controls. H-A..H-D and F-01..F-18 remain open. There is no production fix,
installed-wheel or runtime-matrix evidence, or independent reviewer dispatch.

## Return to Orc

The authorized finite diagnostic is exhausted. Recommend that the Orc adjudicate
this evidence and choose a bounded investigation of the allocation/mapping cause
or an explicitly approved reader/runtime alternative. Do not infer an unlimited
or higher production ceiling, an unsandboxed fallback, or a verified import policy.

The existing optional LibreOffice+bubblewrap boundary has not demonstrated native
conversion feasibility within either the original or amended finite AS envelope.
Diagnostic systemd provided working local aggregate memory/quota/cleanup controls,
but does not authorize or prove a public runtime dependency policy. No successful
alternative or non-Linux portability result was measured. Base dependencies,
production limits, installed CLI and draft/release state remain unchanged.

Kernel charged-memory and descendant-controller semantics are documented in the
[Linux cgroup v2 reference](https://docs.kernel.org/admin-guide/cgroup-v2.html).
In particular, memory.max is a kernel charge/reclaim/OOM boundary which can be
temporarily exceeded; it is not an exact instantaneous RSS ceiling. The live local
observations above, rather than documentation alone, support this return.
