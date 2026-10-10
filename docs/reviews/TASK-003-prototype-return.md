# TASK-003 phase 1: feasibility blocker

Date: 2026-10-06 UTC. Executor: Codex, PROJECT / AGENT on indes-front.
Starting HEAD: `558f7d7f13bd428e85829f86c0f21c30eb9b5126`.
Authority: the frozen TASK-003 technical brief at `ee4629b1aee910cdc5c13033327b11019f273447`.
Disposition: phase 1 incomplete; 0/4 milestones. Return to ttree Orc.
No production integration, local CLI replacement, release, or independent reviewer
dispatch occurred.

## Preflight and threat model

- The worktree started clean on task-001-office-pdf. Remote HEAD matched the start
  SHA. PR #1 was OPEN/DRAFT. Production files still matched `9d420db`.
- Host: indes-front, Arch Linux, kernel 7.2.8-arch1-2. Python 3.12.14,
  LibreOffice 26.8.0.3 680(Build:3), bubblewrap 0.13.0. Existing tools only.
- Observed available memory: 18,495 MiB. Home filesystem: 47 GiB available.
  Host capacity is not the authorized per-process address-space budget.
- Threats to address before integration: native-reader network and host-file access;
  escaping descendants; resource exhaustion during parsing, decompression and
  tokenization; oversized IPC; temporary artifacts and inherited configuration.
- The proposed reader command uses mandatory `--unshare-all`, private PID/proc,
  `--die-with-parent`, `--new-session`, and `--clearenv`. It exposes distribution
  runtime `/usr` read-only, font configuration and the two distribution LibreOffice
  bootstrap files read-only, minimal `/dev`, and one private `/work` directory.
  `/tmp` points to `/work/tmp`. No host home, run, sockets, or general /etc mount.
  HOME/profile/output/temp stay private. `MALLOC_ARENA_MAX=1` is explicit.
- Intended import requires OLE magic and `--infilter=MS Word 97`. The attempt
  stopped during synthetic fixture generation, before this import was possible.
  Neither a command line nor successful namespace setup establishes real-reader
  containment. All live controls after fixture generation remain unrun.
- Child limits: 20 s wall, 15 s CPU and 768 MiB address space per process;
  inherited by descendants. Response/diagnostic files have a 12 MiB file-size cap;
  core dumps are disabled. Outer test: 115 s wall, 60 s CPU per process, 768 MiB
  address space, current user thread count plus 64 process slots, and a disposable
  user/network/PID namespace. No real external requests are made.
- These are prototype controls, not acceptance evidence for an aggregate process
  tree CPU/memory budget. That proof and all worker controls remain pending.

## Observed failure

Run from the repository:

```bash
bash review/task-003/run_prototype.sh .tmp/task-003-prototype-final
bash review/task-003/run_prototype.sh .tmp/task-003-prototype-direct --direct-reader
```

Both attempts use a short synthetic UTF-8 source and request Word 97 DOC output
inside the intended boundary. Neither produced the DOC fixture. The prototype
returned exit 1; bubblewrap reported the reader's exit 139, with a `std::bad_alloc`
diagnostic. No conversion text or private parser content is in the evidence.

| Attempt | Elapsed | Sampled peak tree RSS | Sampled maximum process virtual size | Reader exit |
| --- | ---: | ---: | ---: | ---: |
| Installed launcher | 1.1758 s | 144,556 KiB | 786,432 KiB | 139 |
| Direct soffice.bin | 0.8531 s | 138,632 KiB | 786,432 KiB | 139 |

The observed maximum virtual size equals the 768 MiB ceiling. RSS is much lower.
The evidence supports address-space pressure as a technical hypothesis for the
failure. It does not prove that increasing the ceiling would complete conversion.
No higher-ceiling or unsandboxed conversion was attempted.

Samples are taken every approximately 10 ms from the outer private /proc and can
miss short peaks. Tree RSS sums processes and can count shared pages more than once.
`wait4` CPU/RSS fields describe the bubblewrap wrapper only; they exclude reader
descendants that were reaped inside the namespace. Do not use those fields as
reader CPU or tree RSS evidence. The raw JSON separates these fields.

## Bounded alternatives tested

1. Initial private layout lacked /tmp. LibreOffice returned `no valid pipe path`.
   Adding only a private /tmp alias fixed that startup-path issue.
2. Read-only font configuration, the distribution bootstrap files, and one malloc
   arena were added without exposing user state or raising limits. The allocation
   failure remained.
3. Direct soffice.bin bypassed the installed launcher. The same allocation failure
   remained under the same namespace and ceiling.

Raw command arrays, return codes, timings and limits are in
`review/task-003/evidence/launcher.json` and `direct.json`. Corresponding stderr
files preserve the synthetic-reader diagnostic. SHA256SUMS covers those artifacts.
Earlier scratch attempts remain local and are listed in the executor checkpoint.

## Return and next actor

The frozen brief requires a successful real-reader prototype before integration
and an Orc amendment before raising the ceiling. Stop here. Keep 0/4 progress.
Production remains unchanged; no F finding is closed by this attempt.

Recommendation to ttree Orc: authorize a bounded diagnostic amendment to measure
the minimum finite DOC address-space envelope while preserving mandatory isolation
and explicit CPU/wall bounds, or nominate an approved reader/runtime alternative.
Keep the distinction between virtual address space and resident memory explicit.
The executor cannot replace the frozen address-space cap with an RSS-only cap.
Any runtime/tool change requires the appropriate authority; none is installed here.

Unrun acceptance: actual DOC import/output and latency; network/filesystem/PID
positive and denial controls; denied/missing-boundary behavior; real-reader timeout
and setsid cleanup; PDF/DOCX/IPC prototype; all phase 2 fixes; installed-wheel,
dependency/advisory, artifact and runtime matrix checks; independent Claude review;
final Orc adjudication. H-A..H-D remain unverified.
