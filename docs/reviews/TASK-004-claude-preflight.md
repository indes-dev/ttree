# TASK-004 — independent Claude revalidation: phase 1 preflight

Date: 2026-10-08 (America/Sao_Paulo). Reviewer: independent Claude Code session,
PROJECT / AGENT. This is a Claude review, not a human approval or a release grant.
Authority: frozen `docs/reviews/TASK-004-claude-revalidation-brief.md` at
`97ba3efa79fd5a0c15bdb42b704ba4cbb76a976e`; decision 0011 under 0004/0006.

## Actor, runtime and independence

| Item | Value |
|---|---|
| Runtime | Claude Code CLI, existing configured auth/model (Claude Opus 5.5) |
| Reviewer session ID | `84aaceda-8cd6-4bfc-a9b3-c43de4420112` (from `CLAUDE_CODE_SESSION_ID`) |
| Host / start folder | indes-front (Arch Linux, kernel 7.2.8-arch1-2, 12 CPUs) / `/home/zak` |
| Source | `/home/zak/projects/ttree`; review artifacts in a separate git worktree |
| GitHub identity | `indes-dev` (gh keyring); receipts are commit-linked PR comments |

This session is distinct from the Codex implementation executor
(`01a11301-0e33-7d32-8637-b370df3c0d52`) and the Codex ttree Orc session. It did not
read implementation transcripts, private contracts, credentials or other projects.
No model override, provider change, paid upgrade or new credential was used.

## Exact inputs

| Input | SHA / digest | Check |
|---|---|---|
| Start, local and remote head | `97ba3efa79fd5a0c15bdb42b704ba4cbb76a976e` | `git ls-remote`, `gh pr view 1`: OPEN, draft |
| Production/build/test | `4382916510f91b065e45d6fdfa7b1243b174d75f` | `git diff --name-only 4382916..97ba3ef` touches only `docs/reviews/` and `review/task-003/` |
| Executor evidence | `780c9744b64efca22a31a2914177d09166528a0d` | ancestor of start head |
| Native diagnostic | `41d325737734bcd9b65d4ebf632970178165dbaf` | ancestor of start head |
| Original findings | `bac3684ea3fa36b44e5db8b124c97d14f65374ab` | `TASK-002-claude-findings.md` |
| Application wheel | `7bfa4127407bddfe01c3dbfb79f9f19f3631eb95a1b0939e626d4e273753a0cf` | measured bytes match; offline copy byte-identical (`cmp`) |
| sdist | `02f28180e87518e89d875576eb510f4a63890ece85a24f78161bbe817e136c32` | measured bytes match executor table |
| Offline `SHA256SUMS` | `b8672d7d2caa0ea33971bf743543f12b28f63fa67cc0955d34f701323005a5c8` | measured; all 14 listed entries `sha256sum -c` OK |
| Manifest | source `4382916…`, target CPython 3.12 / Linux x86_64 | read from `.tmp/offline-final-2/manifest.json` |

Production drift: none. Production, tests, build scripts, locks, README, workflow,
`pyproject.toml` and `hatch_build.py` are identical between `4382916` and the start head.

Project-local runtimes (installed non-editable, module path under site-packages):

| Env | Python | tiktoken | pypdf |
|---|---|---|---|
| `.tmp/matrix-310` | 3.10.22 | 0.12.0 | 6.19.0 |
| `.tmp/matrix-311` | 3.11.17 | 0.12.0 | 6.19.0 |
| `.tmp/matrix-312` | 3.12.14 | 0.14.0 | 6.19.0 |
| `.tmp/matrix-314` | 3.14.7 | 0.12.0 | 6.19.0 |

Byte equality of these installed modules with the pinned wheel is a phase 2 check.
Host tools present: `prlimit`, `timeout`, `unshare`, `bwrap`, `jq`, `uv`, `gh`, `git`.
`/proc/sys/user/max_user_namespaces` is 127101 (unprivileged user namespaces enabled).

## Threat model

1. Hostile files inside a scanned tree: PDF CPU/memory floods, recovery paths and
   ciphers; DOCX ZIP lying sizes, honest expansion, member counts, duplicate names,
   XML DTD/entities in any encoding, deep/wide XML; huge or undecodable text.
2. Hostile names and concurrent writers: control/format/line-break characters,
   non-UTF-8 bytes, symlinks at root/ancestor/descendant, live replacement races.
3. Agent consumers: completeness signals (`--strict`, schema-1 JSON, null versus
   zero), forged human tree lines, strict-parser interoperability of JSON paths.
4. Worker containment: oversized IPC, setsid/fork descendants, coordinator death,
   unavailable or denied user/PID namespaces, deadline coverage, coordinator memory.
5. Supply chain and distribution: pypdf floor/advisories, hash-locked closure,
   dirty-checkout inclusion, tamper/missing-hash failures, offline install.
6. Legacy DOC: no native command/fallback reachable; native evidence audit only.

Out of scope: macOS/Windows execution (no runner), native reader execution or any
repeat of exhausted imports/exports, new readers/caps/dependencies, private data.

## Effective outer limits for this review

Every hostile batch runs as
`timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0 <python> …`
with `TMPDIR` and all fixtures under the project `.tmp/task-004/`. Fixtures are
scaled and synthetic; no multi-GiB bomb is built. The production worker ceilings
(15 s wall, 10 s CPU, 512 MiB AS, 12 MiB response) are not changed by the harness.
Base workers contain no network code; the only network-related control is the
offline-install loopback/denial pair, which runs in disposable network namespaces.
No real external request is made by any test. Read-only GitHub API calls are used
only for receipts, CI metadata and the dated pypdf advisory refresh.

## Controls known to be unavailable here

- macOS and Windows runtime behavior (no runner; code inspection only).
- Linux hosts that deny unprivileged user namespaces by policy (for example
  AppArmor-restricted distributions): only simulated locally; CI history is evidence.
- Native DOC positive/denial/timeout/macro/DDE controls: not authorized in TASK-004.
- Multi-GiB memory growth: replaced by scaled fixtures and actual-cap evidence.

## Next

Phase 2 runs independent probes (`review/task-004/`), the production suites in all
four environments, installed-wheel provenance and artifact controls, then audits
the native evidence. Phase 3 commits the disposition matrix and a COMMENTED review.
