# TASK-003 — independent base distribution and runtime return

Date: 2026-10-08 UTC. Executor: Codex, PROJECT / AGENT, indes-front.
The independent base batch passed candidate validation under amendment 2.
The original task remains **0/4**: native phase-1 acceptance is open.
No finding is self-closed. Independent Claude review and Orc per-ID adjudication
remain required. PR #1 stays draft.

## Exact inputs and implementation

Production, tests, build scripts, locks and README were validated at
**4382916510f91b065e45d6fdfa7b1243b174d75f**. The evidence commit containing this
report adds review harness/evidence only; its full SHA is in the verified PR receipt.
It does not replace the artifact's source revision with a later documentation SHA.

Distribution foundation: ad30142bb4bffb242ef1125e8c67784d8261cd53.
Worker-parent identity and namespace-capable CI image:
1e15b31c68b23654868a967304ba4387c67e7ddb.
Final path/correctness fix and live artifact controls: 4382916510f91b065e45d6fdfa7b1243b174d75f.
Earlier candidate stages remain in the base-proof, base-integration,
document-correctness and native-import return reports.

The final path fix validates directory components removed by lexical `..`
normalization, then reopens the normalized path with no-follow descriptors for
actual reads. A live rename moves the checked directory below an outside parent;
the read still counts the legitimate file, not the outside synthetic sentinel.
The scheduling hook delegates every open to the kernel. Separate live file and
directory symlink replacement tests also pass. Ordinary EACCES/EPERM descendants
are `unreadable`; replacement failures remain `changed`. Known bytes survive.
Worker startup also rejects adoption after the original coordinator dies before
exec; this closes the parent-death-signal installation race.

## Installed wheel and dependency floors

Each environment installed the same non-editable wheel. The recorded module paths
are under that environment's site-packages, with no source-tree import fallback.
Python 3.10/3.11 runtimes were installed only under project `.tmp/python` with
`uv python install --no-bin --no-registry`. Host tools and the installed user CLI
were not changed.

| Linux x86_64 runtime | Direct dependency selection | Tests | Seconds | Exit |
|---|---|---:|---:|---:|
| CPython 3.10.22 | tiktoken 0.12.0 / pypdf 6.19.0 | 32 | 20.926 | 0 |
| CPython 3.11.17 | tiktoken 0.12.0 / pypdf 6.19.0 | 32 | 21.176 | 0 |
| CPython 3.12.14 | hash-locked tiktoken 0.14.0 / pypdf 6.19.0 | 32 | 19.868 | 0 |
| CPython 3.14.7 | tiktoken 0.12.0 / pypdf 6.19.0 | 32 | 21.532 | 0 |

The production suite covers actual workers, 1,100-level traversal, real descriptor
races, kernel-denied namespaces, real oversized IPC, setsid teardown, coordinator
death, default XML expansion/depth, encodings, branch/revision semantics, PDF
warning recovery/empty passwords/unsupported cipher, flat JSON and strict exits.
A real PDF operator flood reaches the one-second aggregate deadline: both roots
remain represented as incomplete `timed_out`. Per-file malformed/cap failures
allow a later normal root to count. The source suite also passed 32 tests in 13.154 s.

Both actual GitHub Actions runs for 4382916 succeeded, with four lowest-direct
jobs and one hash-locked installed-artifact job each:
[PR run](https://github.com/indes-dev/ttree/actions/runs/37791878792),
[push run](https://github.com/indes-dev/ttree/actions/runs/37791870305).
The PR log records 32 tests passing in all five jobs and actual direct floors
tiktoken 0.12.0 / pypdf 6.19.0 in all four lowest-direct environments.
The earlier ubuntu-latest runs failed because mandatory namespaces were denied.
Selecting ubuntu-22.04 fixed the environment; no sysctl or containment rule changed.
The dated 51-record primary advisory snapshot remains in the document-correctness
evidence. Its range check is evidence for that snapshot, not a future security claim.

## Actual production caps and agent examples

`verify_production_caps.py` ran the installed CPython 3.12 wheel. Ten live cases
passed in **5.1803 s**: sparse input 64 MiB + 1, plain text 1,000,001 characters,
selected XML aggregate above 8 MiB with every part below 4 MiB, XML elements above
100,000, DOCX 1,000,001 characters, 4,097 ZIP members, lying ZIP metadata, 2,001 PDF
pages, PDF text above 1,000,000 characters and a positively lowered input cap.
Every case returned strict exit 3, null failed tokens, known original bytes and
incomplete totals; the following normal root counted four tokens.
The lying-size case fails real ZIP CRC validation. It does not establish that the
entire 5 MiB member was returned to the parser. Actual streaming expansion caps
are demonstrated separately by honest per-part/aggregate cases and the base proof.

`verify_agent_examples.py` captured real commands, stdout/stderr, parsed results and
timing. Normal DOCX/PDF/BOM UTF-16/empty text gave tokens **4/3/4/0**, complete total
11 and exit 0. Normal family wall **0.8925 s**, waited user CPU **0.763274 s**, system
CPU **0.122347 s**, maximum waited-process RSS **106180 KiB**. RSS is Linux child
rusage high-water, not aggregate cgroup memory; the normal measurement is the first
child run. Subsequent RSS fields are explicitly cumulative.

```sh
python -m ttree.cli --json --strict normal.docx normal.pdf utf16.txt empty.txt # 0
python -m ttree.cli --json --strict legacy.doc latin1.txt                    # 3
python -m ttree.cli --json legacy.doc                                       # 0
python -m ttree.cli --json --strict normal.docx legacy.doc missing           # 1
python -m ttree.cli --json --limit-wall-seconds 0 normal.pdf                 # 2
```

Legacy DOC is `unsupported`, null tokens, incomplete and known bytes. Undecodable
text is `not_utf8`. Missing roots retain null bytes/tokens. JSON alone preserves
exit compatibility. Invalid configuration is argparse usage output, before a JSON
scan exists. Successful/result invocations emit one newline-terminated JSON object
and empty stderr. No extracted text or reader diagnostics are emitted.

## Distribution integrity

Wheel and sdist use exact file allowlists. `hatch_build.py` checks the final
inventory and rejects unexpected implicit Hatch inclusions. The sdist contains
code, tests, build inputs, locks, workflow, vocabulary and licenses. The wheel
contains runtime code/data, notices and standard generated metadata only.
Public review material, hostile fixtures, environments and local sentinels are absent.

The tracked export fixes SOURCE_DATE_EPOCH to the exact commit date. Twelve real
artifact controls passed in **5.2454 s**: repeated tracked wheel/sdist equality,
whole offline-artifact equality, root/src/tests/license dirty sentinels excluded,
required inputs/licenses retained, unexpected implicit `.hgignore` inclusion
clearly rejected, missing hash rejected, actual wheel byte modification rejected,
and paired real loopback/network-denial controls. Synthetic sentinels were removed.
No private document or large hostile fixture is committed or packaged.

The outer disposable network namespace enables loopback and records one successful
synthetic listener connection. A nested fresh network namespace cannot reach that
listener. Inside it, an empty-cache, no-index, hash-enforced installation of all
nine wheels succeeds; installed strict JSON/DOC quarantine/missing-root checks pass.
The listener receives no second connection. This proves the offline installation
control; it does not claim successful native-reader boundary validation.

Artifact target is **CPython 3.12 / Linux x86_64** only. The complete declared closure
includes requests, urllib3, idna, charset-normalizer and certifi; none was stripped.
Build tools are separately hash pinned. `pip download --require-hashes` selects
the chosen wheels. Manifest records target, source SHA, versions, lock digest,
build metadata and native DOC inactivity. Wheels remain project-local, not released.

| Integrity item | SHA-256 |
|---|---|
| Application wheel | `7bfa4127407bddfe01c3dbfb79f9f19f3631eb95a1b0939e626d4e273753a0cf` |
| sdist | `02f28180e87518e89d875576eb510f4a63890ece85a24f78161bbe817e136c32` |
| Runtime dependency lock | `54b42ab94295f072a0d32ae9115d4e2d3667aba9c97f3e829b74028a0f564f14` |
| Application + dependency install lock | `6ec6d8da78ea598dd8f781fa7799c30a49855938190ede8d48e6a5738a18d585` |
| Offline artifact SHA256SUMS file | `b8672d7d2caa0ea33971bf743543f12b28f63fa67cc0955d34f701323005a5c8` |

The digest is prepared here for a separately authorized release channel. Checksums
establish byte integrity; they do not prove origin. No tag, release, signature,
merge or installed CLI update occurred.

## Candidate finding and hypothesis coverage

Every row awaits independent review and Orc adjudication. “Candidate addressed”
describes executor evidence; it is not a finding closure or release approval.

| ID | Candidate disposition and evidence |
|---|---|
| F-01 | Candidate addressed: bounded PDF worker/tokenization, page/character limits, real operator-flood deadline, recovery/cross-root tests. |
| F-02 | **Open**: unsafe native path quarantined; no native fallback. Pinned real DOC import failed at every granted AS step. Intended DOC support remains unmet. |
| F-03 | Candidate addressed: actual bounded ZIP member streaming, 4/8 MiB caps, depth/elements/members, lying-size CRC failure under hard outer bounds. |
| F-04 | Candidate addressed: pypdf floor 6.19.0, dated advisory ranges, actual floor installs and four successful lowest-direct CI jobs; locked artifact CI. |
| F-05 | Candidate addressed: frozen schema 1, flat root entry `.`, path/base64 fields, null unknowns, totals and strict precedence 2/1/3/0 in installed wheel. |
| F-06 | Candidate addressed: BOM UTF-16/32 before binary decision; unknown undecodable content stays incomplete. |
| F-07 | Candidate addressed: public warning handler counts without formatting; recovered/damaged empty and nonempty PDFs remain partial. |
| F-08 | Candidate addressed: iterative scan/aggregation/render, 1,100-level tree, finite input/path/entry/deadline and worker envelopes. |
| F-09 | Candidate addressed: C0/C1/DEL/Cf/Cs human escaping; JSON native serialization and POSIX byte-path round trip. Released-version routing remains Orc-owned. |
| F-10 | Candidate addressed: public Expat DTD/entity handlers; actual UTF-8/16/32 hostile declaration files fail incomplete. |
| F-11 | Candidate addressed: one supported Choice or Fallback, skipped del/moveFrom, strict namespaces/notes, duplicate members rejected. |
| F-12 | Candidate addressed: explicit/ancestor symlink incomplete, descendant link intentional exclusion; normalized `..` cannot bypass validation. |
| F-13 | Candidate addressed: missing roots survive, null unknowns and combined incomplete; strict precedence remains exit 1. |
| F-14 | Candidate addressed: only empty PDF password tried; locked files encrypted, unsupported cipher fixed incomplete, no traceback. |
| F-15 | **Partial/open native**: base PID namespace/pidfd teardown covers setsid/crash/coordinator loss, bounded private work and fresh CPU allowances. Native final CPU proof passed; native reader acceptance/timeout remains open. |
| F-16 | Candidate addressed: exact final distribution inventories, tracked export, real root/src/tests/license sentinels and implicit-input fail-closed build. |
| F-17 | Candidate addressed for CPython 3.12/Linux x86_64: full hashed closure, manifest/checksums, missing-hash/tamper failures and repeat equality. No release digest publication. |
| F-18 | Candidate addressed for base claims: README explains actual caps, links/formats, null/partial semantics, strict JSON, Linux containment, offline target and inactive DOC. Complete document-support outcome remains open. |
| H-A | Live file/directory symlink races and `..` directory reparent race pass with actual opens/renames/worker reads and synthetic outside sentinels. No claim of general filesystem confidentiality isolation for base workers. |
| H-B | **Unverified**: no working macro positive control; no suppression claim. Native inactive. |
| H-C | **Unverified**: no DDE/OLE positive-control evidence; no suppression claim. Native inactive. |
| H-D | Linux installed wheel verified on Python 3.10/3.11/3.12/3.14. macOS/Windows unverified; no artifact or native support claim for them. |

## Reproduction and return gate

From the repository, use existing project-local build/runtime tools. Reproduce with
fresh output paths and outer `timeout --kill-after=1 115 prlimit --as=2147483648
--cpu=60 --core=0`; set TMPDIR to the project's `.tmp`.
Run `scripts/build_tracked.py --revision 4382916510f91b065e45d6fdfa7b1243b174d75f`;
then build the target artifact with `scripts/build_offline.py`. Pass fresh work,
artifact and packages directories to `review/task-003/verify_artifact.py`.
Run `verify_production_caps.py` and `verify_agent_examples.py` with the installed
environment's interpreter symlink, not its resolved underlying Python binary.
The artifact-repeat harness must start at the pinned revision, because it repeats
HEAD. Per-runtime suite commands and complete versions/module locations are in
`review/task-003/evidence/distribution-runtime/runtime-matrix.json`.

Evidence directory contains raw suite logs, concrete examples, timing, production
cap results, artifact inventories/manifest/checksum list, hash negative-control
logs, actual CI job metadata/floor excerpt and its own SHA256SUMS. Harness-only
failed attempts/corrections are disclosed in summary.json; they are not passing
controls. No multi-GiB hostile fixture was reproduced. All task-created native
scopes were previously collected; final user unit query found no ttree units.

Next actor: **ttree Orc**. Review the exhausted native packet at
41d325737734bcd9b65d4ebf632970178165dbaf before any native adapter/default/envelope
change. Collect distinct Claude revalidation of exact production 4382916 and the
receipt's evidence SHA, then adjudicate each ID. Native network/filesystem/PID
positive/denial controls, actual missing/denied boundary invocation and real-reader
timeout remain unrun. No reviewer, Relay or Eryon job was dispatched by this executor.
The independent base batch is complete; the overall native document outcome is open.
