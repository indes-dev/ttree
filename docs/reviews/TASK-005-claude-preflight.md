# TASK-005 — independent Claude review of the changed candidate: phase 1 preflight

Date: 2026-10-09 (America/Sao_Paulo). Reviewer: independent Claude Code session,
PROJECT / AGENT. This is a Claude review, not a human approval or a release grant.
Authority: frozen `docs/reviews/TASK-005-changed-candidate-review-brief.md` at
`758a6cc0e00c6409cac2b46e59aa7b08ec41cd3b`; decision 0013 under 0004/0006/0012.

## Actor, runtime and independence

| Item | Value |
|---|---|
| Runtime | Claude Code CLI, existing configured auth/model (Claude Opus 5.5) |
| Reviewer session ID | `84aaceda-8cd6-4bfc-a9b3-c43de4420112` (from `CLAUDE_CODE_SESSION_ID`; equals the brief) |
| Host / start folder | indes-front (Arch Linux, kernel 7.2.8-arch1-2, 12 CPUs) / `/home/zak` |
| Source | `/home/zak/projects/ttree`; review artifacts in a separate git worktree, branch `task-005-review` |
| GitHub identity | `indes-dev` (gh keyring); receipts are commit-linked PR comments |

Distinct from the Codex executor and the Codex ttree Orc. No implementation transcript,
private contract, credential or other project was read. No model/provider change.

## Exact inputs

| Input | SHA / digest | Check |
|---|---|---|
| Start, local and remote head | `758a6cc0e00c6409cac2b46e59aa7b08ec41cd3b` | `git ls-remote`; `gh pr view 1`: OPEN, draft, same head |
| Production/build/test/README | `4c07f5a06a80a02002dbfecc73331be6886d0180` | ancestor; `git diff --name-only 4c07f5a 758a6cc` touches only `docs/reviews/` and `review/` |
| Executor evidence | `cae2000fbaa143aff904d84545b85395951f3777` | ancestor; four amendment-3 checksum lists, 43 entries, all OK |
| Native observation | `6d47c42f10f0413df07c8ea9e7e52bbf1f7858ec` | ancestor; audit only |
| Prior independent evidence | `1826300ae8d6d9ab30d09a159a21c922c388079f` | covers production `4382916` only; it does not approve `4c07f5a` |
| Application wheel | `926c0af25050cbad17b2305c21f0e39f0deb4fcaef14fc5d460861bab53e6e1b` | measured; offline copy byte-identical (`cmp`) |
| sdist | `83a658cc0a8de6f7fade3dea54ecdd9cd24bea5e550fda5799ecc7164843ad86` | measured |
| Offline `SHA256SUMS` | `e872bab11fd69a6fae9c194b86ca4e7c2c2a8789c376392e506d4162e23a19a2` | measured; all 14 entries `sha256sum -c` OK |
| Manifest | source `4c07f5a…`, target CPython 3.12 / Linux x86_64, `pypdf 6.19.0` | read from `.tmp/amendment-3-offline/manifest.json` |

## Installed provenance (independent)

`review/task-005/installed_provenance.py` compares every `ttree/` file in the wheel with
each env's site-packages. It also imports `ttree` with `-I` from a private temporary cwd.

| Env | Interpreter | Files equal to wheel | Extras / editable `.pth` | Import location |
|---|---|---|---|---|
| matrix-310 | 3.10.22 | 10/10 | none / none | site-packages |
| matrix-311 | 3.11.17 | 10/10 | none / none | site-packages |
| matrix-312 | 3.12.14 | 10/10 | none / none | site-packages |
| matrix-314 | 3.14.7 | 10/10 | none / none | site-packages |

## CI and recorded suites

- Live CI (`ci_and_advisories.py`): runs 37956678593/37956687810 (`4c07f5a`),
  37957300961/37957309454 (`cae2000`) and 37987338348/37987346604 (`758a6cc`). Each has
  locked-artifact plus lowest-direct 3.10/3.11/3.12/3.14, all success.
- Recorded executor installed suites: 37/37 OK on 3.10/3.11/3.12/3.14 (31–34 s). These are
  executor evidence; phase 2 runs the five new regressions independently.
- pypdf advisories, refreshed 2026-10-09T20:58:37Z from the GitHub advisory API: 51 total,
  48 affect 6.1.0, 0 affect 6.19.0. Floor unchanged: `pypdf>=6.19.0,<7`.

## Threats, limits and unavailable controls

- Every phase 2 batch: `timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0`,
  TMPDIR under the project `.tmp/task-005/`, benign synthetic inputs, worker caps unchanged.
- Installed code runs only from the non-editable matrix envs with `-I`.
- Not executed in this task (brief): previously classifier-denied separate F-03/F-07/F-10/
  F-11/F-12/F-14/base-F-15/H-A controls; native reader execution; unchanged full matrices.
  These remain open coverage gaps.

Evidence: `review/task-005/evidence/` (`SHA256SUMS` there).
