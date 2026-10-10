# TASK-004 — independent Claude revalidation: findings and dispositions

Date: 2026-10-08 (America/Sao_Paulo). Reviewer session
`84aaceda-8cd6-4bfc-a9b3-c43de4420112`, independent Claude Code (Claude Opus 5.5),
PROJECT / AGENT. Authority: frozen brief `docs/reviews/TASK-004-claude-revalidation-brief.md`
at `97ba3ef`. This is a Claude review, not a human approval, per-ID closure or release
grant. The ttree Orc adjudicates each ID.

Earlier stages: preflight `7c5094b` (`TASK-004-claude-preflight.md`), partial phase 2
`cd8ee5d` (`TASK-004-claude-phase2-partial.md`). This document supersedes the partial
phase 2 "unverified coverage" list where later controls ran (marked below).

## Inputs and identity

| Input | Value |
|---|---|
| Production/build/test | `4382916510f91b065e45d6fdfa7b1243b174d75f` (no drift up to `cd8ee5d`: `git diff 4382916 HEAD` over `src tests scripts locks .github pyproject.toml README.md` is empty) |
| Executor evidence | `780c9744b64efca22a31a2914177d09166528a0d` |
| Native diagnostic | `41d325737734bcd9b65d4ebf632970178165dbaf` |
| Application wheel | `7bfa4127407bddfe01c3dbfb79f9f19f3631eb95a1b0939e626d4e273753a0cf` |
| sdist | `02f28180e87518e89d875576eb510f4a63890ece85a24f78161bbe817e136c32` |
| Offline `SHA256SUMS` | `b8672d7d2caa0ea33971bf743543f12b28f63fa67cc0955d34f701323005a5c8` |
| Phase 3 start head | local = remote = PR head `cd8ee5de0244fb1f375c57511c28f129d9b0cd22`, PR #1 OPEN/draft |

## Environment, limits, timings and memory scope

- Host indes-front, Arch Linux, kernel 7.2.8-arch1-2, 12 CPUs. Project-local envs
  `matrix-310/311/312/314` with the measured wheel installed non-editable.
- Every batch: `timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0`,
  TMPDIR under the project `.tmp/task-004/`, synthetic fixtures only. Original worker
  ceilings unchanged (per worker 15 s wall / 10 s CPU / 512 MiB AS / 12 MiB FSIZE).
  No batch reached an outer limit.
- Offline controls ran inside `unshare -rn` (new user+network namespace, no route).
- Timings: production suites 14.0–16.4 s per runtime; worker fixed cost 0.19 s/file
  (40 files in 7.59 s); retained native imports 1.05–1.14 s each.
- Memory scope: coordinator/supervisor peak RSS was not measured independently; it is
  bounded only by the 2 GiB outer AS. Worker memory is bounded by the 512 MiB AS rlimit.
  Native figures below are the executor's retained cgroup readings, not new runs.

## Independent results

| Control | Result | Evidence |
|---|---|---|
| Installed module provenance | 10/10 files byte-equal to the wheel, no extras, in all four envs | `installed-provenance.txt` |
| Production suites (`unittest discover -s tests`) | 32/32 OK on CPython 3.10.22, 3.11.17, 3.12.14, 3.14.7 | `suite-3*.log` |
| Wheel inventory | 15 entries: 8 modules, vocabulary + licence, dist-info; no tests/review/native files | `wheel-inventory.txt` |
| Repeat tracked build at `4382916` | wheel and sdist byte-identical to the measured artifact (and `build.json`), with untracked files present in the checkout | `rebuild-hashes.txt`, `rebuild-4382916.log` |
| Offline install in netns | external connect denied, loopback ok; hash-locked install rc 0 and smoke `counted`/5 tokens; tampered pypdf wheel rc 1 (hash error); missing hash rc 1 (hash error) | `offline-controls.json` |
| CI at `4382916` | runs 37791878792 (pull_request) and 37791870305 (push): all five jobs success (locked-artifact; lowest-direct 3.10/3.11/3.12/3.14) | `ci-and-advisories.txt` |
| pypdf advisories, refreshed 2026-10-08T20:04:19Z (GitHub advisory API) | 51 total; 48 affect 6.1.0; 0 affect 6.19.0 (floor `pypdf>=6.19.0,<7`) | `ci-and-advisories.txt` |
| DOC quarantine and exit precedence | `a.doc`/`B.DOC` → `unsupported`, tokens null, correct bytes (11), incomplete; sibling `.md` counted; root/total incomplete. Exit: non-strict 0; strict partial 3; strict complete 0; strict partial + missing 1; non-strict missing 1 | `contract-checks.txt` |
| No external command path | the only `subprocess.Popen` in `src/` is the Python worker in `bounded.py` | inspection |
| Multi-root human total | `Total: [≥3 tok \| partial]` with a missing root | `contract-checks.txt` |
| Probes P-A..P-F | see "New and residual defects" | `probes-312.json` |
| Native evidence audit | 6/6 retained checksums OK; outcome fields read below | `native-audit.txt` |

## New and residual defects

| ID | Finding | Label |
|---|---|---|
| N-1 | The worker is launched as `sys.executable -m ttree.worker` without isolated mode and without a fixed `cwd`. For `-m`, Python puts the working directory first on the module path, and the worker inherits the caller's working directory, which is the scanned tree in the common `ttree .` use. Module resolution therefore depends on scanned content, and it happens before the worker's containment applies. Class: untrusted-path module resolution. This is not present in v0.1.0 or the installed 0.2.0 CLI. | open defect, high by inspection (runtime not performed) |
| N-2 (P-A) | The worker's file-size limit (= 12 MiB `response_bytes`) also bounds the input snapshot. A 13 MiB DOCX with little text is `failed`; 11 MiB is `counted`. The 64 MiB input default is unreachable for documents above 12 MiB. | open defect |
| N-3 (P-B) | A worker per file costs 0.19 s, so the 120 s scan deadline completes at most about 630 files. Partial signalling is honest (`partial`, per-file `timed_out`). | open defect (capability gap) |
| F-09 residual (P-C) | U+2028 in a name is emitted unescaped in human output (2 newline-terminated lines become 3 under `str.splitlines()`); backslash is not escaped, so escapes are ambiguous. JSON is correct (P-F). | open defect |
| N-4 (P-D) | An unreadable directory reports `tokens: 0`, `bytes: 0` with `complete: false` instead of null for unknown values; totals inherit 0. | open defect (contract, low) |
| N-5 (P-E) | Where unprivileged user namespaces are denied, even plain text is `limits_unavailable` (fail-closed; exit 0 non-strict, as documented). The tool counts nothing on such hosts or off Linux. | capability not delivered (platform) |

## F-01..F-18 disposition matrix

| ID | Original issue | Independent disposition | Label |
|---|---|---|---|
| F-01 | PDF has no time/page/work bound | By inspection, extraction runs in the bounded worker with a 2,000-page cap, a 1,000,000-character cap and worker rlimits. The deadline/timeout path was exercised (P-B). Hostile PDF flood/recovery runs were not executed independently and remain executor evidence. | temporary containment; unverified coverage (hostile PDF runs) |
| F-02 | `.doc` reaches LibreOffice, external fetch | DOC never reaches a native command or fallback (only the Python worker is spawned). Fixed `unsupported`/null/incomplete with correct bytes and strict precedence were verified. Native DOC remains open per Orc. | temporary containment (verified); capability not delivered (DOC) |
| F-03 | DOCX budget trusts declared ZIP sizes | By inspection, the caps count actual decompressed bytes per part and in aggregate, plus member-count and duplicate-name rejection. Lying-size runs were not executed independently. | unverified coverage (correction present by inspection) |
| F-04 | `pypdf>=6.1` floor, advisories | Floor `>=6.19.0,<7`. Advisories refreshed 2026-10-08T20:04:19Z: 0 of 51 affect 6.19.0. Lowest-direct CI passes on four runtimes. | independently verified base correction (dated) |
| F-05 | Exit 0 for incomplete/failed | Exit precedence 1 > 3 > 0 and the `--strict` gate verified. | independently verified base correction |
| F-06 | Non-UTF-8 text silently excluded | Covered by the production suites passing on four runtimes. There is no separate independent probe. | independently verified base correction (suite level only) |
| F-07 | PDF recovery loss not partial | Not executed independently (README states recovery warnings make results incomplete). | unverified coverage |
| F-08 | Deep trees / large files crash run | Traversal and rendering are iterative by inspection. A large file no longer aborts the run, but files from 12 to 64 MiB fail (N-2). Deep-tree runs were not executed independently. | open defect (N-2); unverified coverage (deep trees) |
| F-09 | Control characters/newlines raw | Newline, ESC, invalid bytes and bidi override are escaped (suite `test_human_control_escape_and_posix_raw_path_roundtrip`). U+2028 and backslash ambiguity remain (P-C). | open defect (residual) |
| F-10 | DTD guard bypassed by UTF-16 | By inspection, the doctype/entity handlers reject at the expat level after its own encoding detection. No independent UTF-16/32 run. | unverified coverage (correction present by inspection) |
| F-11 | DOCX double counting | By inspection: duplicate members are rejected, and single AlternateContent branch and `del`/`moveFrom` are omitted. Not executed independently. | unverified coverage |
| F-12 | Symlinked root yields nothing | By inspection: `O_NOFOLLOW` descriptor-relative traversal, with symlinks shown and not followed. No independent run. | unverified coverage |
| F-13 | Multi-root total omits missing root | `Total: [≥3 tok \| partial]` verified. | independently verified base correction |
| F-14 | Empty user password PDF | By inspection, `decrypt("")` is attempted. Not executed independently. | unverified coverage |
| F-15 | DOC timeout cleanup | The native part remains open (Orc). Base-worker setsid/parent-death teardown is executor evidence only. | capability not delivered (native); unverified coverage (base teardown) |
| F-16 | sdist includes untracked files | Rebuild with untracked files present is byte-identical, and the inventory is exact. | independently verified base correction |
| F-17 | Offline resolution unlocked | Hash-locked offline install passes in netns. Tampered and missing hashes fail. | independently verified base correction |
| F-18 | README claims exceed behaviour | Most claims now match: DOC inactive, Linux-only validation, cap list, exit codes. Three claims exceed observed behaviour: the "64 MiB input" default (N-2), "human output escapes … format characters" for line separators and backslash (F-09 residual), and "unknown file counts are null" for unreadable directories (N-4). | open defect (documentation residual) |

## H-A..H-D coverage

| ID | Coverage | Label |
|---|---|---|
| H-A symlink swap race | Descriptor-relative `O_NOFOLLOW` opens plus a private snapshot, by inspection. No live race run independently. | unverified coverage |
| H-B macro execution | Native DOC is inactive, so there is no exposure in this candidate. Suppression is unproven. | capability not delivered; unverified coverage |
| H-C DDE/OLE live update | As H-B. | capability not delivered; unverified coverage |
| H-D platforms | Linux CPython 3.10/3.11/3.12/3.14 verified (suites, provenance, CI). macOS/Windows unverified. Hosts that deny unprivileged user namespaces are non-functional (N-5). | independently verified (Linux 3.10–3.14); capability not delivered (other platforms) |

## Native evidence audit (retained `41d3257`, no execution)

- The retained `SHA256SUMS` validates 6/6. The run started at `02012e72`; `passed`, `native_import_success` and
  `native_controls_complete` are all false; failure: "finite native import ceilings exhausted".
- Synthetic controls (accepted, within their boundary):
  - Memory: 128 MiB cgroup limit, `oom_group_kill` 1, `setsid` child accounted, `populated` 0 after.
  - CPU: throttled to 15.01 s with a 12 ms overshoot; whole tree terminated; cgroups removed and scopes collected.
- Imports per reader AS step (cgroup `memory.max` 768 MiB aggregate):

  | AS step | Status | Peak cgroup memory | CPU | OOM events | Stderr class |
  |---|---|---|---|---|---|
  | 768 MiB | failed | 65 MiB | 0.79 s | 0 | none (empty) |
  | 1024 MiB | failed | 59 MiB | 0.79 s | 0 | `std::bad_alloc` |
  | 1536 MiB | failed | 82 MiB | 0.84 s | 0 | component `DeploymentException` |
  | 2048 MiB | failed | 71 MiB | 0.83 s | 0 | `std::bad_alloc` |

  None of the steps produced the expected text.
- Not established: a working native reader, a production envelope, or the actual native
  network/filesystem/PID/timeout denial and macro/DDE controls. All of these are unrun.

**Hypotheses** (marked, not established):

- *H1 (hypothesis):* `RLIMIT_AS` counts virtual reservations, not resident use. Allocation fails
  while peak cgroup memory stays at 59–82 MiB, about 12–29× under the AS step. This fits `bad_alloc`
  with no cgroup OOM, but does not explain why 2048 MiB still fails.
- *H2 (hypothesis):* the minimal sandbox lacks a resource needed for component registration
  or profile initialisation. This fits the 1536 MiB `DeploymentException` and the silent 768 MiB
  failure. The non-monotonic outcome across AS steps suggests AS is not the only variable.
- Raising AS is not inferred as a remedy, and no new reader is proposed.

**Recommended smallest discriminating diagnostic (recommendation only; requires a
frozen Orc instruction):**

- Run one bounded repeat at a single existing step (1024 MiB), with the same pinned fixture,
  sandbox, cgroup limits and batch wall.
- Change one thing: in the existing poll loop, sample the reader's `/proc/<pid>/status`
  `VmPeak`/`VmSize`, and retain the exit status/signal.
- Read the result:
  - `VmPeak` at or near the AS limit at failure supports H1.
  - `VmPeak` far below the limit with the same failure points away from H1, towards H2.
- It needs no new tool, cap change or host package.

## Recommendations

**Base safety (DOCX/PDF/text candidate):**

1. Fix N-1 before any release or wider use: run the worker in isolated interpreter mode
   from a fixed trusted working directory, and add a regression test for scanned-tree
   module shadowing.
2. Fix N-2: separate the snapshot size bound from the response bound, or document a lower
   effective input cap.
3. Escape U+2028/U+2029 and backslash in human output (F-09 residual), and emit null for
   unknown directory counts (N-4).
4. Correct the three README claims (F-18 residual).
5. Before per-ID closure, have the hostile-fixture controls still marked unverified
   (F-01/F-03/F-07/F-10/F-11/F-12/F-14, H-A, base teardown) executed by a session that can
   run them. The executor's evidence exists, but it was not independently reproduced here.

**Full requested outcome (offline DOCX/PDF + optional DOC):**

1. DOC remains capability not delivered: native import failed at every authorized step.
   Proceed only through the single diagnostic above under a frozen instruction.
2. The scan-throughput ceiling (N-3) and the namespace requirement (N-5) limit the offline
   outcome for large trees and for restricted or non-Linux hosts. Treat them as scope
   decisions for the Orc, not as base-safety blockers.
3. macOS/Windows claims stay out until validated.

## Unavailable or not executed

- Hostile-fixture runs are listed under unverified coverage above. The runtime safety
  classifier withheld reviewer responses while building them. The human chose to record
  statuses only and not to retry. These runs remain executor evidence.
- No native reader execution, no import/export repetition, no tracing tools and no
  host packages, per the brief.

## Evidence

All files are under `review/task-004/evidence/`, checksummed in `SHA256SUMS` there. The
scripts are in `review/task-004/`:
`probe.py`, `run_suites.sh`, `installed_provenance.py`, `ci_and_advisories.py`, `rebuild.sh`,
`offline_controls.py`, `run_offline_controls.sh`, `contract_checks.sh`, `native_audit.py`,
`post_receipt.py`.
