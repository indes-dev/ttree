# TASK-003 — amendment 1: bounded DOC diagnostic

Status: issued and frozen, 2026-10-06 UTC. Issuer: ttree Orc, Codex.
Parent: `TASK-003-remediation-brief.md` at
ee4629b1aee910cdc5c13033327b11019f273447.
Return: b1447338ebc9aa1cd74b5798174139b198cba2f1.
Adjudication: companion `TASK-003-prototype-adjudication.md`.
All parent requirements remain except the explicitly authorized diagnostic
address-space variation below. This is not a production-default amendment.

## Grant and stop boundary

The existing implementation executor may amend only the synthetic diagnostic
prototype/evidence, using existing tools on the current Linux execution host.
Transient user-systemd units for these bounded tests are authorized; no privileged
cgroup setup, persistent service, new host package or harness change is authorized.
Keep mandatory bubblewrap namespaces, private profile/temp, explicit runtime
mounts, cleared environment, no real external network and no private documents.
Return missing/denied controls or failed feasibility to the Orc. Never substitute
unsandboxed execution, sampled RSS or RLIMIT_RSS for the approved boundary.

Production integration and phase 2 remain blocked pending Orc adjudication of this
diagnostic and the complete phase-1 boundary. Progress remains 0/4. No F/H closure,
independent reviewer dispatch or release is authorized by this amendment.

## Finite envelope

1. Each real-reader diagnostic runs in a dedicated cgroup v2 beneath the existing
   user manager. Require kernel readback before the reader starts: memory.max
   805306368 (768 MiB), memory.swap.max 0, pids.max 64. Use aggregate CPU quota
   no greater than one CPU. Confirm reader descendants remain in this group and
   cannot reach cgroup files or the user-manager bus inside the sandbox.
2. Preserve 20 s reader wall time, 15 s per-process CPU, response/file limits,
   disabled core dumps, private PID namespace and finite whole-batch deadline.
   Also abort on 15 s aggregate cgroup CPU consumption; record supervision interval
   and measured overshoot, with at most 250 ms CPU beyond the threshold. Choose a
   quota period/poll interval that can meet this bound. A wrapper wait4 is not
   aggregate accounting. Keep the outer diagnostic batch deadline at 115 s and
   its existing 60 s per-process CPU limit; return on exhaustion.
3. DOC-only RLIMIT_AS soft AND hard limits may be tried at 1024, 1536 and 2048 MiB,
   in order, stopping at first successful stage. The trusted outer diagnostic
   wrapper may have a finite AS ceiling of at most 2048 MiB so its inherited hard
   limit does not invalidate the trial. Change no other worker's default envelope.
   Memory or process limits may not be raised to make these trials pass.
4. A trusted supervisor outside the reader cgroup must terminate the whole job on
   timeout/OOM/failure, including descendants that call setsid. Verify absence of
   survivors and private outputs after cleanup. Do not expose the supervisor's
   privileges/control sockets to the reader. Units must be stopped/collected at
   completion; document and clean only task-created transient resources.

## Ordered diagnostic and proof

First validate aggregate memory enforcement with a small synthetic allocator and
descendant under a reduced 64 or 128 MiB cgroup limit. Bound allocation, wall time,
CPU and process count; retain kernel counters and observed failure/cleanup. Prove
that an escaping-session child is still accounted for and terminated. Readback
alone is not an enforcement test. If controls cannot be established, stop.

Separate DOC fixture generation from DOC import. Do not repeat the two known
768 MiB export failures unchanged. Generate one tiny native OLE/Word 97 synthetic
fixture within the approved isolation, trying the ordered higher AS ceilings only
as needed. Preserve its provenance and digest; do not invent a successful fixture.
Test import of that fixture first at 768 MiB, then the ordered higher ceilings if
needed, under the same aggregate controls. Stop if 2048 MiB still fails. Generation
and import must have distinct measurements and outcomes. Explicitly changing only
AS and adding aggregate controls is new diagnostic evidence, not a claimed fix of
the known baseline. Each batch remains bounded; record batches and cumulative time.

If conversion succeeds, continue the parent phase-1 controls within these ceilings:
real-reader network/filesystem denial with bounded positive controls in the
disposable test environment, failed/missing namespace tool through the actual
invocation path, real-reader timeout and setsid cleanup, PDF/DOCX worker bounds,
actual oversized IPC rejection and aggregate CPU/memory accounting. Do not count
existence checks, ordinary small responses or wrapper-only metrics as these proofs.
Use no public exploit recipe or private input in the evidence.

Record exact commands, versions, AS per stage, cgroup settings/membership,
memory.peak/events, cpu.stat, elapsed time, exit/status and cleanup evidence.
Retain negative attempts. Distinguish kernel charged memory, sampled RSS, virtual
size and wrapper accounting. Include unrun controls and reasons.

## Return before production policy

Make a substantive diagnostic/evidence commit, normal push after checking the
remote head, and a verified exact-SHA gh receipt. Update the executor checkpoint
and devlog with the real executor session. Return to the Orc with a finite proposed
import envelope and its boundary proof; do not integrate it automatically.

Explain whether the optional production DOC boundary can use the existing
LibreOffice+bubblewrap dependency policy, or needs an additional capability/runtime.
Compare only tested alternatives and state portability limits. Diagnostic systemd
use does not authorize a new public dependency. Base DOCX/PDF dependencies remain
unchanged. The Orc must adjudicate before accepting production limits or continuing
phase 2. All original review, strict/JSON, packaging and release gates remain.
