# TASK-002 — Claude preflight and threat model

Phase: 1 of the issued brief `docs/reviews/TASK-002-cross-validation.md` (commit `ac3c322`).
Reviewer: independent Claude Code session, dispatched by the maintainer's direct
instruction. Posted under the configured GitHub identity `indes-dev`; this is a
Claude review, not a separate human approval.
Started: 2026-10-06T15:35Z (UTC).

## Baseline

| Item | Value |
|---|---|
| Repository | `indes-dev/ttree`, draft PR [#1](https://github.com/indes-dev/ttree/pull/1) |
| Candidate branch | `task-001-office-pdf` |
| Public base (`v0.1.0`) | `0f1d6bbd9dbb02ebc91dd0180ec4f81c09bbb361` |
| Implementation under review | `9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e` (tree `2aae0d18`) |
| PR head at preflight | `dfacc2084538140f788cdf6a30d3e823dcbfe7b4` |
| Head vs implementation | only `docs/reviews/` changed (3 files); `src/`, `tests/`, `scripts/`, `pyproject.toml`, `README.md`, `THIRD_PARTY.md` identical |

The implementation baseline is therefore `9d420db`. A later source, dependency,
vocabulary or build change requires a new pinned baseline before a final verdict.

## Runtime and environment

- Review runtime: Claude Code 2.1.291 (`claude --version`). Model reported by the
  runtime: Claude Opus 5.5 (`claude-opus-5-5`). No model, billing or credential change.
- Host: Linux x86_64 (Arch-based workstation), 12 CPUs, 31 GiB RAM.
- Isolation: separate git worktree on local branch `task-002-claude-review`
  tracking `origin/task-001-office-pdf`. The maintainer's checkout is untouched.
- Python: CPython 3.12.14 (uv-managed) and CPython 3.14.7 (system), each in a
  project-local venv under the untracked `.review/` directory.
- Resolved runtime set (both interpreters): tiktoken 0.14.0, pypdf 6.19.0,
  regex 2026.9.29, requests 2.34.2, urllib3 2.8.0, idna 3.20,
  charset-normalizer 3.5.2, certifi 2026.7.22.
- Tools: uv 0.12.23, LibreOffice 26.8.0.3 (already installed; not added for this
  review), util-linux `unshare`/`prlimit`, `bwrap`, `systemd-run --user`.
- Existing suite: `python -m unittest discover -s tests` → 15 tests OK on 3.12.14
  and on 3.14.7. This reproduces the executor's count; it is not security evidence.

## Assets

1. Confidentiality of the documents being counted and of their paths
   (text must never be printed, logged, uploaded or left in temporary files).
2. Integrity of the scanned tree: no writes, lock files or conversions beside
   originals; no modification of user configuration (e.g. LibreOffice profile).
3. Host availability: CPU, memory, disk, processes, terminal state.
4. Network silence: no egress during first use or DOC conversion.
5. Correctness of the estimate as consumed by humans **and agents**: a total
   must not look complete when it is not.
6. Supply-chain integrity: vocabulary hash, wheel contents, dependency set,
   offline artifact checksums.

## Trust boundaries and attacker-controlled inputs

| Boundary | Attacker controls | Code path |
|---|---|---|
| Filesystem tree → `inspect()` | names (control chars, newlines, non-UTF-8, option-like), depth, symlinks, special files, races, file sizes | `cli.py:65-119`, `render()` |
| DOCX bytes → `zipfile` + `xml.etree` | ZIP central directory (sizes, duplicates, entry count), XML encoding, DTD/entities, nesting depth | `documents.py:58-92` |
| PDF bytes → pypdf | xref, object graph, page tree, filters/streams, fonts | `documents.py:95-119` |
| DOC bytes → LibreOffice | **real content type** (LibreOffice sniffs; a `.doc` may be RTF/HTML/ODF/etc.), macros, fields, OLE/DDE, external links, conversion cost | `documents.py:122-181` |
| Extracted text → tiktoken | arbitrary-length pieces, whitespace runs, special-token-looking strings | `tokenizer.py`, `cli.py:95,115` |
| stdout/stderr/exit code → agent | — (the consumer must interpret them) | `measure_label()`, `main()` |
| Package/offline artifact → installer | dependency resolution, wheels, checksums | `pyproject.toml`, `scripts/*` |

## Unintended effects to look for

- Code execution (macros, DDE/OLE, scripts) or external access (links, remote
  images, includes) while reading untrusted files, especially through LibreOffice.
- Unbounded CPU/memory/time per file or per tree (zip/stream bombs, page-tree
  amplification, tokenizer worst cases, huge plain files, aggregate DOC timeouts).
- Process leaks (LibreOffice children surviving a timeout), temporary-file leaks.
- Disclosure through tracebacks, parser logs/warnings, or crash output.
- Terminal/agent output injection via filenames or link targets.
- Silent exclusion of content with exit status 0 (agent misreports a lower bound
  as a complete total).

## Initial hypotheses from code reading (to verify or refute in phase 2)

- H1. The DOCX DTD/entity guard checks ASCII bytes only; a UTF-16 part may bypass
  it and reach expat entity handling.
- H2. DOCX size budget trusts the declared ZIP `file_size`; duplicate members may
  be counted twice; extraction recursion depth is unbounded (caught or not?).
- H3. PDF extraction has no page, time or memory bound; a shared page tree may
  amplify work beyond file size.
- H4. LibreOffice detects content by signature, so a `.doc` may be imported by a
  non-Word filter (HTML/RTF/ODF) whose behaviour differs from the configured Writer
  link/macro settings.
- H5. `-env:UserInstallation` profile hardening is only partly verified by mocks;
  timeout cleanup was only tested with a mocked `Popen`.
- H6. Exit status is 0 for incomplete or failed extraction; only a missing path
  sets 1. Multi-root totals omit missing roots without a marker in stdout.
- H7. Filenames and link targets are printed raw (control characters, newlines);
  non-UTF-8 filenames may crash `print()`.
- H8. Deep directory trees reach Python's recursion limit in `inspect()`.
- H9. Plain files are read fully into memory and tokenized without a size bound.
- H10. Tokenizer worst-case inputs (long pieces without whitespace) may be
  super-linear.

These are hypotheses, not findings.

## Method and limits

- Hostile tests run under `prlimit` (address space, CPU seconds, process count)
  and `timeout`, inside `$TMPDIR`-style throwaway directories. Network checks use
  `unshare -Urn` (user + network namespace) with an observing listener on the
  namespace loopback.
- Only public code and synthetic fixtures are used. No private documents,
  contracts, credentials or user configuration are read.
- macOS and Windows are not available to this reviewer; they will be reported
  as unverified with a validation path.
- No production code is changed in this review. Remedies go to the Orc.

## Plan

Phase 2 commits reproduction tests/scripts plus
`docs/reviews/TASK-002-claude-validation.md`; phase 3 commits
`docs/reviews/TASK-002-claude-findings.md` and submits a `gh pr review --comment`.
