# TASK-005 — independent Claude review of the changed candidate: findings

Date: 2026-10-09 (America/Sao_Paulo). Reviewer session
`84aaceda-8cd6-4bfc-a9b3-c43de4420112`, independent Claude Code (Claude Opus 5.5),
PROJECT / AGENT. Authority: frozen brief `docs/reviews/TASK-005-changed-candidate-review-brief.md`
at `758a6cc`. This is a Claude review, not a human approval, per-ID closure, TASK-003
closure or release grant. The ttree Orc adjudicates each ID.

Earlier stage: preflight `dc0e6f6` (`TASK-005-claude-preflight.md`). The prior TASK-004 review
(`1826300`) covered production `4382916` only and does not approve `4c07f5a` or the new bytes.

## Inputs and identity

| Input | Value |
|---|---|
| Production/build/test | `4c07f5a06a80a02002dbfecc73331be6886d0180` |
| Executor evidence | `cae2000fbaa143aff904d84545b85395951f3777` |
| Native observation (read-only audit) | `6d47c42f10f0413df07c8ea9e7e52bbf1f7858ec` |
| Coordination head at start | `758a6cc0e00c6409cac2b46e59aa7b08ec41cd3b`; descendants touch only `docs/reviews/` and `review/` |
| Application wheel | `926c0af25050cbad17b2305c21f0e39f0deb4fcaef14fc5d460861bab53e6e1b` |
| sdist | `83a658cc0a8de6f7fade3dea54ecdd9cd24bea5e550fda5799ecc7164843ad86` |
| `build.json` | `a81534494e3a5480a0d80c6e5f3f3aef64cba3cf28ce5f469b55060d931c0271` |
| Offline `SHA256SUMS` | `e872bab11fd69a6fae9c194b86ca4e7c2c2a8789c376392e506d4162e23a19a2` |

## Environment and limits

- Host indes-front, Arch Linux, kernel 7.2.8-arch1-2. Existing project-local envs
  `matrix-310/311/312/314` (CPython 3.10.22, 3.11.17, 3.12.14, 3.14.7). The new wheel is installed
  non-editable, and the 10/10 installed files are byte-equal to the wheel (preflight).
- Every batch ran under `timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0`,
  from a private cwd, with TMPDIR under the project `.tmp/task-005/`. No batch reached an outer limit.
- Inputs were benign synthetic only. No hostile archive, lying size, decompression bomb or
  external request. No native reader execution.

## Independent results (new-review executions)

| Control | Result | Evidence |
|---|---|---|
| Five new regressions on the installed wheel, run from a private cwd with `python -I -m unittest discover -s/-t <abs tests>` | 5/5 OK on 3.10, 3.11, 3.12 and 3.14 (4.4–5.5 s per env); `ttree` resolved from each env's site-packages | `regressions-3*.log` |
| Source review `4382916..4c07f5a` (`bounded.py`, `cli.py`, `scan.py`, `worker.py`; 39+/10−) | Corrections match the adjudicated items. No regression found; one hygiene note (below) | inspection |
| Live DOC quarantine and exit precedence on the new console script (3.12) | Inert plain-text `legacy.doc` gives `unsupported`, tokens null, bytes 26, incomplete. Siblings are counted, and root/total are incomplete with known sum 8. Exit codes: non-strict 0; strict partial 3; strict complete file 0; strict partial + missing 1; non-strict missing 1. Human multi-root total is `Total: [≥4 tok \| partial]` | `live-checks-312.json` (A) |
| Live real-clock scan deadline: 40 tiny files in 4 directories with `--limit-scan-seconds 1` | Exit 3 after 1.043 s with empty stderr. 3 unenumerated directories are `timed_out` with tokens/bytes null. The partially scanned directory, root and total show known sums 20 tokens / 130 bytes with `complete: false`. 5 files counted, 5 `timed_out`, and no incomplete entry reports 0 tokens | `live-checks-312.json` (B) |
| Same 40 files with no lowered limit (control) | Exit 0 in 8.121 s on the final wheel | `live-checks-312.json` |
| Repeat tracked build at `4c07f5a` | wheel, sdist and `build.json` byte-identical to the pinned artifact | `rebuild-hashes.txt`, `rebuild-4c07f5a.log` |
| Package inventory | Wheel has 15 entries (8 modules, vocabulary and licence, dist-info). sdist has only tracked project files; no `review/`, `docs/reviews/` or `.tmp` | `wheel-inventory.txt` |
| Offline artifact | The `indes_ttree` wheel in `wheels/` hashes to `926c0af…` and is pinned in `install-lock.txt`. Phase 1 checked the 14/14 `SHA256SUMS` | inspection, preflight |
| Fresh offline install in `unshare -rn` | External connect denied; loopback ok. Hash-locked install rc 0; smoke `counted`/5 tokens. Tampered pypdf wheel rc 1 (hash error); missing hash rc 1 (hash error). One run against the new artifact | `offline-controls.json` |
| CI and advisories | Phase 1 (preflight): six runs at `4c07f5a`/`cae2000`/`758a6cc`, all five jobs success. pypdf advisories refreshed 2026-10-09T20:58:37Z: 0 of 51 affect 6.19.0. Not refreshed again in this phase | `ci-and-advisories.txt` |
| Native observation audit, read-only | See below | `native-audit.txt` |

The injected-clock regression (`test_unenumerated_timed_out_directory_and_unknown_only_parent`)
is a deterministic simulation that patches `time.monotonic` and `os.scandir`. The live
real-clock check (B) is separate evidence that elapsed-time enforcement works on the installed
console script.

## Pass/fail for the changed items

| ID | Independent result | Remaining scope | Label |
|---|---|---|---|
| N-1 | **Pass.** The worker now launches as `sys.executable -I -m ttree.worker` with `cwd=` a private `mkdtemp` directory and an allowlisted env. The regression places shadow `ttree`, `tiktoken`, `pypdf`, `ctypes`, `json` and `sitecustomize` modules in the caller cwd: no marker is written, and normal text/DOCX/PDF count `[4,4,3]` in 4 runtimes | The guarantee covers the worker and the installed console script. A parent started as `python -m ttree.cli` from an untrusted cwd is Python's own bootstrap behaviour and outside this correction (the test comment says so). Informational | independently verified correction |
| N-2 | **Pass.** During the snapshot, worker `RLIMIT_FSIZE` = max(input, response). The snapshot loop rejects at input+1 before writing. After the snapshot, FSIZE drops to the effective response limit, and the supervisor enforces response bytes incrementally (`len(output)+len(chunk) > limit`). Stored padded DOCX at 11, 13 and 64 MiB counts. 64 MiB+1 is `too_large`, and the next root still counts. A 512-byte response limit does not lower input. A 12 MiB input limit rejects 13 MiB | Benign stored padding only. Hostile expansion and lying-size remain prior unverified coverage (F-03) | independently verified correction |
| N-4 | **Pass.** `known_sum` gives null when no contribution is known, 0 only for a fully enumerated empty directory, and known sums otherwise. Excluded media and links now carry known 0 tokens. Verified by the real unreadable-directory regression and live with unenumerated `timed_out` directories | — | independently verified correction |
| F-05 | **Pass.** Exit precedence 1 > 3 > 0 and `--strict` re-verified live on the new console script | — | independently verified base correction |
| F-08 | **Pass** for the large-file part. Files from 12 to 64 MiB are no longer forced to fail (N-2). | Deep-tree runs not executed independently | independently verified correction (large files); unverified coverage (deep trees) |
| F-09 | **Pass.** Backslash is escaped first (`\\`), so escapes are unambiguous. Zl/Zp (U+2028/U+2029) join Cc/Cf/Cs and C1 in `\uXXXX` escaping. 5 lines under `splitlines()` in 4 runtimes; JSON paths preserved | Other categories (e.g. Zs, Co) are not escaped and the README does not claim them | independently verified correction |
| F-18 | **Pass** for the three TASK-004 residuals: 64 MiB input, line-separator/backslash escaping, and null for unknown directories. The new README text was checked against code and evidence: snapshot/IPC split, `-I`/private cwd, null policy, no namespace fallback, and profile figures (9.049 s / 9.010 s CPU, 93,404 KiB waited-process RSS, 14–22 ms, 228–231 ms, about 530 per 120 s match `profile.json`) | Two low documentation notes, D-1 and D-2 below | independently verified correction (with low notes) |

### Low notes (non-blocking, for Orc disposition)

- **D-1:** The README says post-snapshot output is "capped at 12 MiB". The code caps it at the
  *effective* response limit, which is 12 MiB by default and lower when `--limit-response-bytes`
  is lowered. Accurate at the default only.
- **D-2:** The N-3 profile (`amendment-3-base/profile.json`) records a provisional wheel
  `cf5d8f00…` and "final tracked artifact pending; runtime module equality will be verified".
  This review did not independently compare provisional and final modules. The live 40-file
  control on the final wheel (8.121 s, exit 0) corroborates the order of magnitude.
- **H-1 (hygiene):** in `bounded.py` `supervise()`, `received` is incremented but never read.
  It has no behavioural effect.
- **H-2 (hygiene):** the rebuild log shows a `DeprecationWarning` from
  `scripts/build_tracked.py:49`, where `tar.extractall` is called without an extraction filter.
  The archive is the script's own freshly built sdist, so this is not an exposure today. An
  explicit `filter="data"` would future-proof it for Python 3.14 defaults.

## Explicit outcomes kept open

- **N-3 (throughput):** this is a local linear projection, not a fixed entry cap. The profile
  gives about 530 identical tiny files per 120 s; this review's single control gives 40 files in
  8.121 s, about 590 per 120 s, on the same host. The RSS figure is the waited-process maximum, not
  aggregate memory. Larger batches hit the deadline and remain honestly incomplete (verified live).
  Label: open capability gap (Orc scope decision).
- **N-5 (namespaces):** confirmed by source. Failure of `unshare(CLONE_NEWUSER)`, the
  uid/gid maps, `unshare(CLONE_NEWPID)`, `prctl(PDEATHSIG)` or a non-Linux platform raises
  `limits_unavailable`, with no fallback. Restricted hosts were not exercised live in this review.
  Label: capability not delivered (platform).
- **DOC:** quarantined (`unsupported`, null, incomplete; no native path; `.doc` is in
  `UNSUPPORTED` before any worker launch). Label: capability not delivered.
- **Platforms:** Linux CPython 3.10/3.11/3.12/3.14 only. macOS and Windows are unverified.

## F-01..F-18 disposition matrix (carried forward and updated)

| ID | Disposition at `4c07f5a` | Label |
|---|---|---|
| F-01 | Unchanged since TASK-004: bounded worker, 2,000 pages, 1,000,000 characters, rlimits. Hostile PDF runs not executed independently | temporary containment; unverified coverage (hostile PDF runs) |
| F-02 | DOC never reaches a native command; quarantine re-verified live | temporary containment (verified); capability not delivered (DOC) |
| F-03 | Unchanged; actual-byte DOCX budgets by inspection. Previously denied control not recreated | unverified coverage (correction present by inspection) |
| F-04 | Floor `>=6.19.0,<7`; 0 of 51 advisories affect 6.19.0 (dated 2026-10-09T20:58:37Z); CI lowest-direct passes | independently verified base correction (dated) |
| F-05 | Re-verified live | independently verified base correction |
| F-06 | Unchanged code path. Not re-run in TASK-005 (executor suites 37/37 are reference only) | independently verified base correction (TASK-004, suite level; unchanged) |
| F-07 | Not executed independently; previously denied control not recreated | unverified coverage |
| F-08 | Large files verified (N-2); deep trees not run | independently verified correction (large files); unverified coverage (deep trees) |
| F-09 | Residual closed by new escaping, verified in 4 runtimes | independently verified correction |
| F-10 | Unchanged; by inspection only; previously denied control not recreated | unverified coverage (correction present by inspection) |
| F-11 | Unchanged; previously denied control not recreated | unverified coverage |
| F-12 | Unchanged; previously denied control not recreated | unverified coverage |
| F-13 | Multi-root human total with a missing root re-verified live (`Total: [≥4 tok \| partial]`) | independently verified base correction |
| F-14 | Unchanged; previously denied control not recreated | unverified coverage |
| F-15 | Native part open. Base teardown remains executor evidence; previously denied control not recreated | capability not delivered (native); unverified coverage (base teardown) |
| F-16 | Rebuild byte-identical at `4c07f5a`; inventory exact | independently verified base correction (new artifact) |
| F-17 | Fresh offline hash-locked install of the new artifact in netns; tamper and missing hash fail | independently verified base correction (new artifact) |
| F-18 | Prior three residuals corrected; D-1/D-2 low notes | independently verified correction (with low notes) |

## H-A..H-D coverage

| ID | Coverage | Label |
|---|---|---|
| H-A symlink swap race | Unchanged traversal. No live race run; previously denied control not recreated | unverified coverage |
| H-B macro execution | Native DOC inactive. No exposure in this candidate; suppression unproven | capability not delivered; unverified coverage |
| H-C DDE/OLE live update | As H-B | capability not delivered; unverified coverage |
| H-D platforms | Linux CPython 3.10–3.14 verified (regressions, provenance, CI). Other platforms unverified. Namespace-denying hosts are non-functional by design (N-5) | independently verified (Linux 3.10–3.14); capability not delivered (other platforms) |

## Native observation audit (`6d47c42`, read-only, no execution)

- One case at the 1024 MiB AS step. The run started at `907b306`, an ancestor of production.
  Results:
  - reader exit 139 after 4.94 s; stderr class `std::bad_alloc` (2 lines);
  - expected text not observed; `passed` and `native_import_success` false.
- The 7/7 checks pass: pinned fixture, identity, kernel readback, retained final accounting,
  CPU final overshoot (0 s), cleanup with no survivors and the reader cgroup removed, and private
  data removed.
- Virtual size: 212 native samples, 0 dropped, max `VmPeak` = max `VmSize` = 1,048,576 KiB, which
  equals the 1024 MiB AS step exactly. This **supports** the virtual-space-pressure hypothesis (H1)
  but does not prove it is the unique cause, as the retained interpretation states.
- Additional observation: the retained `before_termination` cgroup `memory.peak` reached 796,319,744 B, which is 98.9% of
  `memory.max` 805,306,368 B, with `memory.events` max/oom/oom_kill all 0. The TASK-004 1024 MiB
  step showed 59 MiB. Cgroup memory can include page cache, so this does not show resident
  pressure. It does mean two ceilings were near their limits in this single run, and the
  observation does not discriminate between them.
- No retry, cap change or new reader is inferred or recommended. DOC remains capability not
  delivered.

## Not executed in this review

- The previously classifier-denied F-03/F-07/F-10/F-11/F-12/F-14/base-F-15/H-A controls were
  not recreated, renamed or rerouted.
- Unchanged full suites and every unchanged sentinel/tamper matrix were not re-run. The four-runtime
  executor suites (37/37) are reference only. One offline tamper and one missing-hash run were
  repeated against the new artifact.
- Deep-tree traversal was not run. No restricted-namespace host or macOS/Windows host was used.
- No native reader execution, import/export retry, tracing tool, or host package.
- Advisories were not refreshed after 2026-10-09T20:58:37Z.

## Recommendation to the Orc

All changed-code checks inside this brief passed on the new installed wheel and artifact. This
does **not** complete the safety coverage, which still has the unverified hostile-fixture IDs
above, and it does not deliver DOC. D-1/D-2/H-1/H-2 are low and non-blocking. N-3, N-5, native DOC
and platforms remain Orc scope decisions.

## Evidence

All files are under `review/task-005/evidence/`, checksummed in `SHA256SUMS` there. The scripts
are in `review/task-005/`: `installed_provenance.py`, `ci_and_advisories.py`,
`run_regressions.sh`, `live_checks.py`, `rebuild.sh`, `offline_controls.py`,
`run_offline_controls.sh`, `native_audit.py`.
