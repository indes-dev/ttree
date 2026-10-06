# TASK-003 phase 1 — Orc adjudication

Date: 2026-10-06 UTC. Owner: ttree Orc, Codex.
Executor evidence: b1447338ebc9aa1cd74b5798174139b198cba2f1,
`TASK-003-prototype-return.md`, with receipt:
https://github.com/indes-dev/ttree/pull/1#issuecomment-6025415955.

## Disposition

Accept the executor's stop as required by the frozen brief. Phase 1 remains
incomplete, progress 0/4. Production remains 9d420db; no finding is closed.
Authorize only the finite diagnostic in `TASK-003-amendment-1-doc-diagnostic.md`.
Return its evidence to the Orc before adopting a production envelope or entering
phase 2. Original briefs and the failed-prototype report remain frozen.

The failure occurred while exporting a small synthetic DOC fixture, before native
DOC import. It does not establish the importer's minimum envelope. Both launcher
and direct binary reached 786,432 KiB virtual size at the 768 MiB ceiling; sampled
tree RSS was 138,632–144,556 KiB. Address-space pressure is a supported hypothesis,
not proof of feasibility with a higher ceiling. Wrapper CPU/RSS is not tree usage.

RLIMIT_AS limits virtual mappings, not resident memory. Linux cgroup v2 provides
a separate aggregate charged-memory limit and descendant accounting. Its
memory.max can transiently be exceeded; describe its kernel semantics accurately,
without claiming an exact instantaneous RSS ceiling. Primary references:
[getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html),
[cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html).

## Bounded feasibility check by the Orc

The existing user systemd manager accepted a disposable scope with MemoryMax
805306368, MemorySwapMax 0 and TasksMax 64. A tiny read-only child observed the
matching `memory.max`, `memory.swap.max`, and `pids.max` values in its own cgroup;
the scope exited successfully and was collected. No sudo, package installation,
persistent service or native-reader test was performed. This establishes local
diagnostic capability, not OOM enforcement, containment or portable production
support. The executor must validate those controls as specified in the amendment.

Orc rechecked retained evidence checksums, shell syntax, unchanged production,
matching b144733 local/remote head, and the published executor receipt. These are
evidence-integrity checks, not successful prototype acceptance.

## Follow-up and dependency policy

Separate fixture generation from import, test finite virtual ceilings alongside
aggregate kernel memory controls, and require live enforcement/cleanup evidence.
Keep failed runs and ceilings explicit. No unsandboxed fallback or user-state
exposure is authorized. Namespace smoke, a nonexistent-path check, a small worker
response and process-group cleanup alone cannot establish the respective live
reader, fail-closed, oversized-IPC and escaping-descendant properties.

The diagnostic uses existing host tools. It adds no base dependency and does not
decide whether systemd belongs in the optional public DOC runtime. Keep the two
direct Python dependencies and stdlib DOCX policy. If the proposed production
boundary needs a new runtime dependency, return the measured alternatives and
fail-closed behavior to the Orc; do not silently make public DOC require systemd.

Resume the existing executor through the task harness. Independent Claude must
still revalidate the eventual fixed SHA; final closure remains with the Orc.
PR #1 stays OPEN/DRAFT. No merge, tag, release or installed-CLI change is granted.
