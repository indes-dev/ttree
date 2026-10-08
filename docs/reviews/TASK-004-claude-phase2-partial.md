# TASK-004 — independent Claude revalidation: phase 2 (partial)

Date: 2026-10-08. Reviewer session `84aaceda-8cd6-4bfc-a9b3-c43de4420112`, PROJECT / AGENT.
Production/build/test `4382916510f91b065e45d6fdfa7b1243b174d75f` (no drift). Installed
artifact: wheel `7bfa4127407bddfe01c3dbfb79f9f19f3631eb95a1b0939e626d4e273753a0cf`.
This is a Claude review, not a human approval or release grant.

Every run used `timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0`,
synthetic scaled fixtures and TMPDIR under the project `.tmp/task-004/`. Evidence is in
`review/task-004/evidence/` (see `SHA256SUMS` there).

## Installed artifact and suites

| Check | Result |
|---|---|
| Installed modules vs wheel bytes (`installed_provenance.py`) | 10/10 equal, no extras, in matrix-310/311/312/314 |
| Production suites (`unittest discover -s tests`, installed wheel) | 32/32 OK on 3.10.22, 3.11.17, 3.12.14, 3.14.7 |

## Functional probes (`probe.py`, matrix-312 installed wheel)

| ID | Observation | Label |
|---|---|---|
| P-A | A DOCX of 13 MiB with a few tokens of text reports `failed`; the same at 11 MiB reports `counted`. The worker's file-size limit equals `response_bytes` (12 MiB) and also applies to the input snapshot, so inputs between 12 and 64 MiB cannot be counted. | open defect |
| P-B | 0.19 s of fixed cost per counted file (worker per file); with the 120 s maximum scan deadline, about 630 files is the ceiling for a complete result. Deadline handling is honest (`partial`, per-file `timed_out`). | open defect (capability gap) |
| P-C | U+2028 in a file name is emitted unescaped in human output: 2 newline-delimited lines, 3 by `str.splitlines()`. Backslash is also not escaped. F-09 residual. | open defect |
| P-D | An unreadable directory reports `tokens: 0`, `bytes: 0` with `complete: false`; unknown values are not null. The same applies to the summed JSON/human total. | open defect (contract, low) |
| P-E | With nested user namespaces denied, a plain `.md` reports `limits_unavailable` and the process exits 0 (non-strict). The tool does not function on hosts that deny unprivileged user namespaces, or off Linux. | capability not delivered (platform) |
| P-F | Non-UTF-8 name: JSON with a surrogate escape in `path` was accepted by `jq`; `path_bytes_base64` present. | not a defect (refuted) |

## Code inspection (not executed)

- The base worker is launched as `sys.executable -m ttree.worker` without isolated mode.
  For `-m` launches Python places the working directory first on the module search path
  (inert check: `python -m site` from a scratch directory lists it first). The worker
  therefore resolves modules relative to the caller's working directory, which defaults
  to the scanned tree. Class: untrusted-path module resolution before containment.
  Not present in v0.1.0 or the installed 0.2.0 CLI (neither launches a Python worker).
  Label: open defect, high severity by inspection; runtime confirmation not performed.

## Unverified coverage (blocked in this session)

The runtime safety classifier repeatedly withheld reviewer responses while building
hostile document fixtures and containment controls. The following brief controls
were therefore not independently executed and remain executor-only evidence:

- PDF cipher (empty/locked), page-cap, recovery-warning and continuation controls;
- ZIP member-count, duplicate-name, per-part and aggregate XML caps; DTD in UTF-8/16/32;
  AlternateContent single selection; `del`/`moveFrom` omission and `ins` inclusion;
- strict exit precedence across mixed roots; DOC quarantine with external-command
  negative control; coordinator SIGKILL and surviving-worker scan; symlink-swap race;
- tracked rebuild, dirty-checkout, tamper/missing-hash and offline-install controls;
- CI log audit, dated pypdf advisory refresh, and native evidence audit at `41d3257`.

The Orc decides whether these run in another session or remain executor evidence.
