# TASK-002 — Orc adjudication (phase 4)

Date: 2026-10-06 UTC. Owner: ttree project Orc, Codex.
Operation: public users and agents must count local documents offline, with few
dependencies, bounded work and an explicit indication when an estimate is incomplete.

## Evidence and verdict

Reviewed implementation: `9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e`.
Public release/base: `0f1d6bbd9dbb02ebc91dd0180ec4f81c09bbb361` (v0.1.0).
Review evidence: preflight `b73fd1c6a73a0bc2cc77d917e595e5f1b3fc346d`, validation
`822eecf0f4dc3e01f42860028288cf87f66ef538`, findings
`bac3684ea3fa36b44e5db8b124c97d14f65374ab`.
Independent [Claude review](https://github.com/indes-dev/ttree/pull/1#pullrequestreview-5431309247)
is COMMENTED, submitted against the findings commit; its report explicitly identifies
the implementation SHA. Production source, tests, packaging scripts, dependencies and
README match the reviewed implementation: verified by a zero diff after fast-forwarding
the local branch to the observed remote findings head. PR #1 remains OPEN/DRAFT.

**0.2.0 is not release-ready.** Accept all eighteen findings for remediation. F-01,
F-02 and F-03 block release. The Medium findings also require closure before accepting
the candidate for agents. Include the Low fixes in the same remediation cycle; none
is waived. Acceptance of a finding does not imply acceptance of every proposed remedy.
No source correction, release approval or fresh full adversarial rerun occurred in
this adjudication. The committed reviewer reproductions remain the technical evidence.

Confirmed strengths remain: upstream tokenizer parity, reproducible clean offline
builds, smaller installed footprint, no OCR and no private data in public history.
These do not offset the blocking findings.

## Disposition of every finding

| ID | Disposition and directed correction | Required evidence |
|---|---|---|
| F-01 High | Accept. Isolated PDF worker; wall, CPU, memory, input, page and text/work budgets; aggregate scan deadline. | Shared-stream flood terminates inside effective limits; siblings survive; incomplete status. |
| F-02 High | Accept. Optional DOC requires OS isolation; OLE signature and explicit Word 97 filter are additional checks. No unsandboxed fallback. | Real reader controls demonstrate inaccessible network/home and permitted conversion. Fail closed when isolation cannot start. |
| F-03 High | Accept. Count actual decompressed bytes with bounded chunk reads; streaming XML and structural/work limits; worker resource caps. | Lying-size and honest amplification fixtures respect caps and cannot exhaust the coordinator. |
| F-04 Medium | Accept. Raise pypdf floor to >=6.19.0,<7; lowest-direct dependency job and advisory check. | Floor installation and regression probes pass; record current advisory snapshot. |
| F-05 Medium | Accept --strict and --json; freeze exit codes, completeness and status enum. | Consumers distinguish every incomplete condition without free-text parsing. |
| F-06 Medium | Accept. Decode BOM-marked UTF-16/32 before NUL/binary detection. Recognizable undecodable text is explicitly incomplete. | BOM text counts; Latin-1/text failures carry status and propagate incompleteness. |
| F-07 Medium | Accept. Count PDF WARNING+ records without formatting their contents; conservative partial result. | Damaged page fixture produces partial/complete=false and no parser text leak. |
| F-08 Medium | Accept. Iterative scan, aggregation and rendering; bounded regular-file input; per-entry recovery. | Deep trees and oversized files preserve other roots/siblings without traceback. |
| F-09 Medium | Accept. Escape controls, line breaks and surrogates everywhere in human paths/link targets/errors. | Byte-level output test rules out terminal controls and forged lines; JSON round-trip. |
| F-10 Low | Accept. Reject DTD/entities using public expat callbacks regardless of XML encoding. | UTF-8/16/32 DTD fixtures rejected; no reliance on private ElementTree parser attributes. |
| F-11 Low | Accept. Select one supported AlternateContent branch, omit moveFrom/deleted content, reject duplicate ZIP member names. | Textbox/move/duplicate fixtures; visible content counted once, ambiguous archive rejected. |
| F-12 Low | Accept ambiguity; retain no-follow for explicit roots. Reject automatic root-follow remedy. | Explicit root link is link_not_followed/complete=false; descendants excluded by documented policy. |
| F-13 Low | Accept. Retain missing-root result and propagate incomplete into combined total. | Mixed roots: exit 1, complete=false and human >= marker. |
| F-14 Low | Accept. Try the empty user password only; fail gracefully if unsupported or unsuccessful. | Empty-password fixture counts; protected fixture remains encrypted; no password collection. |
| F-15 Low | Accept. Private temp environment, PID containment, cleanup and aggregate deadline. DOC disabled without verified platform boundary. | setsid descendant is gone; real conversion timeout leaves no outside temp artifacts. |
| F-16 Low | Accept. Explicit package allowlist plus clean tracked-source release build. | Root and in-directory untracked sentinel files absent from sdist/wheel; required source/licenses included. |
| F-17 Low | Accept. Hashed platform lock, hash-enforced download, lock digest in manifest; publish artifact digest with release metadata later. | Locked repeated build and tamper/missing hash rejection; all transitive dependencies preserved. |
| F-18 Low | Accept. Correct claims only after evidence; state supported platforms, limits, exclusions and optional DOC requirements. | README examples checked against installed wheel and JSON schema; no unverified macro/DDE claims. |

## Architecture and minimal dependencies

Keep tiktoken plus pypdf as direct Python dependencies. DOCX remains standard-library
only; PDF reads existing text without OCR. Worker/process control and XML parsing use
the standard library. Do not add a generic document-conversion service or network API.

For optional legacy DOC on Linux, choose LibreOffice within bubblewrap namespaces
and a minimal filesystem view: only the necessary read-only runtime plus private
input, output, profile and temp space; no host home/configuration/sockets. Clear inherited
environment. Isolate networking and descendants. OLE magic and the pinned Word 97
import filter must still be checked. Missing or unusable isolation means
sandbox_unavailable, incomplete; there is no host reader fallback. Users can install
the optional sandbox or convert trusted DOC to DOCX outside ttree. Non-Linux DOC is
unavailable until an equivalent boundary is independently verified. Base DOCX/PDF
users acquire no extra host dependency.

Alternatives considered: a signature/filter-only repair is smaller but does not bound
all native-reader effects; dropping DOC loses the requested operation; mandatory
sandboxing of every basic format adds unnecessary installation burden. Isolating only
the optional native DOC reader retains the requested capability and a small base.
This is a policy choice, not a claim that bubblewrap is secure with arbitrary options.

Bounded feasibility evidence on indes-front: existing bubblewrap ran an unprivileged
--unshare-all/--clearenv private namespace; a Python child could not connect to a
public address and could not see /home/zak. This was a small namespace smoke test,
not a LibreOffice integration/security test. No package or host setting was changed.
The remediation brief starts with a real-reader prototype and positive controls;
stop and return to the Orc if the proposed boundary cannot perform safe conversion.

External facts checked 2026-10-06: [pypdf 6.19.0 release](https://github.com/py-pdf/pypdf/releases/tag/6.19.0)
and the [current high advisory](https://github.com/advisories/GHSA-v247-6f48-mgcj)
support raising the floor; the GitHub advisory query had no further page and included
additional advisories fixed in 6.19.0. This is not a guarantee against new advisories.
[bubblewrap upstream](https://github.com/containers/bubblewrap) documents that policy
comes from the supplied sandbox options. [Python resource](https://docs.python.org/3/library/resource.html)
limits are platform dependent; unsupported limits must not be silently presented as enforced.

## Agent contract and unresolved coverage

The new brief freezes a single JSON document, flat entries, stable statuses and
complete flags, alongside strict exit 3 for incomplete scans (usage 2 and root/fatal
1 retain precedence). Default human-mode exit behavior stays compatible. JSON reports
effective limits and exclusions; it never contains extracted document text or parser
exception strings. Tokens are estimates/lower bounds, not a model billing promise.

| Hypothesis | Current status and validation path |
|---|---|
| H-A symlink race | Unverified. Race disposable entries/directories; use no-follow descriptor access and fstat on POSIX, including stable parser input copies. Do not claim race resistance from an initial is_symlink check. |
| H-B macros | Unverified because the permissive control also did not execute. Require a live positive control or state the feature unverified. Isolation must independently contain effects. |
| H-C DDE/OLE | Unverified without a suitable synthetic Word-authored input. Containment is required regardless; report actual fixture coverage and avoid profile-only promises. |
| H-D platforms | Run Linux Python 3.10/3.11 plus 3.12/3.14 from installed builds. macOS/Windows remain unverified; do not imply supported DOC isolation there. |

## Released-version disclosure and next actors

F-08 and F-09 also affect v0.1.0, with low observed released-version impact. Choose a
normal public hardening issue, class-level description and mitigations. Current evidence
does not justify emergency withdrawal, a CVE request or a claim of secret exposure.
No High finding has been established in v0.1.0. Do not add exploit recipes or private
contracts. The exact issue body is TASK-002-public-hardening-issue.md; its observed
GitHub receipt is added to the phase record. If new evidence shows a sensitive
released-version vulnerability, stop public detail and return disclosure routing to the Orc.

Verified OPEN public tracking issue: [#2](https://github.com/indes-dev/ttree/issues/2).
Its retrieved body matches the committed issue body.

Remediate in the candidate; if 0.2.0 remains blocked, issue a separate v0.1.1 backport
brief for F-08/F-09. This does not authorize publishing either version.

Next: Orc freezes TASK-003; implementation Agent performs bounded prototype, focused
fix commits and validations; independent Claude revalidates the exact fixed SHA;
Orc adjudicates closure of every ID. Each completed stage is committed and communicated
through gh. Keep PR #1 draft, preserve history, and do not merge/tag/release.
