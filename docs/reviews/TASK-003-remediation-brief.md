# TASK-003 — Security and agent-use remediation

Status: issued and frozen, 2026-10-06 UTC. Issuer: ttree project Orc, Codex.
Accepted direction: TASK-002-orc-adjudication.md at
`8a6f563fa01d9b2ced60832b9784cabd30280d8c`.
Do not edit this brief after issue; return proposed scope changes for an amendment.

## Operation, scope and baseline

Public users and agents need to count local DOCX, PDF text and optional DOC offline
with few dependencies, bounded work and explicit incomplete results. This implements
the human's requested document support and independent-review requirements, not a
release authorization. Evidence must show real installed behavior, adverse-input
containment, agent-readable results and a clean reproducible offline artifact.

Repository: indes-dev/ttree. Draft PR #1, branch task-001-office-pdf.
Released base: `0f1d6bbd9dbb02ebc91dd0180ec4f81c09bbb361`.
Reviewed production implementation: `9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e`.
Findings: `bac3684ea3fa36b44e5db8b124c97d14f65374ab`,
docs/reviews/TASK-002-claude-findings.md and its committed probes.
Execution starts from the commit issuing this brief, or a normally fast-forwarded
coordination descendant. Pin the full starting SHA in preflight. Stop on unrelated
production changes or a divergent remote; do not overwrite others' work.

Execution host: indes-front (Arch Linux). Source path: /home/zak/projects/ttree.
Use a local PROJECT / AGENT implementation executor under the Orc's authority.
Independent Claude reviewer must remain distinct from that executor. No inference
session, provider/model change or paid upgrade is launched by issuance of this brief.
Use project-local Python environments and existing host tools. No host package,
sudo, background service, unrelated project or private contract access is granted.

## Phase 1 — bounded prototype before integration

Commit a preflight/threat model and bounded synthetic prototype with environment
versions, effective limits, command lines, exit/status observations and raw timing/RSS
summaries. Post its commit-linked receipt through gh on PR #1. The prototype must:

1. Exercise a real LibreOffice conversion in the intended bubblewrap filesystem,
   network and PID boundary. Expose only needed read-only runtime dependencies and
   private input/output/profile/temp; clear inherited env; no host home/config/sockets.
   Require OLE magic and the Word 97 import filter. No --unshare-*-try or fallback that
   silently drops the required boundary. Probe unavailable and denied user namespaces.
2. Use synthetic positive controls for network and host-file access, then demonstrate
   denial inside isolation. Do not make real external requests: use a disposable
   loopback listener in the outer bounded test namespace. A separate helper probe
   verifies network/filesystem/PID boundaries even if the native fixture does not
   activate a feature. State exactly which controls were live.
3. Demonstrate process-tree cleanup using a setsid descendant and a real-reader
   timeout; temp artifacts stay inside the private work directory. Apply hard outer
   wall/CPU/memory bounds to hostile tests and cap listener/child lifetimes.
4. Prototype PDF/DOCX worker limits and bounded IPC. Run scaled hostile fixtures
   first; never recreate multi-GiB memory growth without an outer enforced cap.
   Record normal synthetic conversion/tokenization latency and memory too.

Maximum default envelope for the implementation: 64 MiB input per regular file;
DOCX XML 4 MiB per selected part and 8 MiB aggregate actual decompressed bytes;
2,000 PDF pages; 1,000,000 extracted Unicode characters per document/text file;
15 s wall / 10 s CPU / 512 MiB address space for a basic file worker;
20 s wall / 15 s CPU / 768 MiB for DOC's conversion process tree;
120 s aggregate scan-work deadline; 100,000 entries; 12 MiB worker response.
Set additional finite XML depth/element and archive-member/work limits based on the
prototype. Defaults may be lower within this envelope with documented measurements;
raising the envelope or dropping a required boundary requires a new Orc amendment.
Effective limits must be named, finite and reported by JSON. Configurable values
must be positive and validated; do not offer an unsafe unlimited DOC fallback.
The deadline covers traversal, snapshotting, parsing and tokenization. If exhausted,
retain completed results and represent skipped work as incomplete. Blocking writes
to a consumer's stdout are outside the scan-work deadline; document that distinction.

Existing namespace smoke proves feasibility only, not DOC integration. If real
conversion cannot work within this policy, stop and return a bounded decision packet
with tested alternatives; do not weaken isolation or silently remove DOC support.
If the prototype succeeds, continue autonomously to phase 2 under this frozen scope.

## Phase 2 — focused corrections

Separate substantive commits for resource containment, optional DOC isolation,
result/filename semantics, DOCX/PDF correctness and distribution integrity. Explain
which F IDs each commit addresses and post completed phase receipts via gh. Production
tests must verify behavior, including cross-root continuation; do not merely assert
the chosen helper's implementation. Preserve review commits and evidence.

- F-01/F-03/F-08/F-15: isolated bounded worker work, including tokenization; coordinator
  never accumulates unbounded document/IPC data. Enforce actual ZIP expansion using
  bounded chunked member reads, streaming XML and structural caps. Cap regular file
  input before and during reads. Traverse, aggregate, sort and render iteratively.
  Per-entry failure preserves siblings/roots; deadline exhaustion has a fixed status.
  Avoid cumulative child CPU limits accidentally penalizing subsequent jobs. All
  descendants must be contained, not merely the initial process group.
- F-02/F-15: optional DOC is Linux + available verified bubblewrap + LibreOffice;
  signature/filter and private profile are defense in depth. Missing LibreOffice is
  reader_unavailable; missing/failed isolation is sandbox_unavailable. No unsandboxed
  fallback. DOCX/PDF acquire no new host tool. Document optional install/recovery route.
- F-04: pypdf>=6.19.0,<7, current advisory snapshot, lowest-direct CI plus normal locked
  artifact CI. Preserve upstream dependency closure rather than deleting unused
  requests dependencies from tiktoken's declared requirements.
- F-06/F-07/F-13: BOM decoding precedes binary tests; unsupported text encoding is
  explicit incomplete. Conservatively record PDF WARNING+ without formatting/logging
  private parser contents. Missing roots survive in results and combined completeness.
- F-09: escape C0/C1, DEL, line breaks, unpaired surrogates and misleading Unicode
  format controls in human names, root paths, link targets and errors. JSON uses proper
  serialization, not the human escaper. No raw parser exceptions/document text.
- F-10/F-11: public xml.parsers.expat callbacks reject DTD/entity declarations across
  encodings. No private ET.XMLParser.parser dependency. Choose one supported
  AlternateContent branch, fallback only if needed, skip moved-from/deleted text;
  reject duplicate ZIP member names instead of selecting ambiguous duplicate data.
- F-12: do not follow symbolic links, including explicit roots; explicit link root
  carries incomplete link_not_followed. Descendant links are excluded by scope.
- F-14: attempt only empty-user-password PDF decryption. No password prompts/guessing;
  unsupported cipher/dependency is a fixed incomplete status, not a traceback.
- H-A: use descriptor-based no-follow reads and fstat, stable private snapshots for
  external/document readers, and directory-relative no-follow traversal on supported
  POSIX. An initial check followed by pathname access is insufficient. Race disposable
  file and directory entries under a bounded test; never use real private targets.

## Frozen machine-readable contract (F-05)

Add opt-in --strict and --json. Preserve normal human display options and default
human exit compatibility. `complete` refers to the documented counting scope;
it does not assert OCR, model billing accuracy or all embedded/non-text content.

Exit codes: 2 usage/invalid configuration; 1 missing root or unrecoverable startup/run
failure; 3 strict-mode incomplete when neither 1 nor 2 applies; otherwise 0.
--json does not imply --strict. Root/per-entry read or reader failures are results,
not fatal startup failures. All known incomplete states propagate regardless of -L.
No stack trace for ordinary malformed input, limit hits or per-entry failure.

--json emits exactly one JSON document and a final newline, no human tree on stdout:

- schema_version: 1; effective_limits: object; roots: array; total: object.
- Each root: path, path_bytes_base64 on POSIX, tokens, bytes, complete, status, entries.
- entries is flat, including the root with relative path "."; each entry has path
  relative to its root, native path_bytes_base64 on POSIX, kind, tokens, bytes,
  complete and status. Kind enum: directory | file | link | missing | other.
- total: tokens, bytes, complete. Unknown entry token/byte values are null. Directory
  and combined values sum known estimates/bytes and propagate complete=false.
  Do not substitute zero for an unread/failed entry. A legitimate empty file has 0.
- JSON string escaping must make control/surrogate names safe. Native byte-path
  fields provide a lossless mapping on POSIX; document native Unicode behavior for
  platforms where byte paths are not available. No extracted text, parser messages
  or arbitrary reader diagnostics in JSON/stderr. Flags -h/--exact/-L/--sort do not
  change schema or omit scanned entries; document their JSON presentation behavior.

Fixed entry/root status enum for schema 1:
`counted | empty | no_text | excluded | unsupported | not_utf8 | reader_unavailable |
sandbox_unavailable | limits_unavailable | encrypted | partial | failed | timed_out |
link_not_followed | unreadable | too_large | missing | changed`.

counted/empty/no_text are complete when the scoped operation completed; no_text means
no selectable text and does not imply OCR was attempted. excluded is complete only
for a documented scope exclusion (known non-text media/binary, descendant symlink).
Recognized but unsupported text-bearing formats such as legacy PPT/XLS/ODT use
unsupported, incomplete. Undecodable expected text uses not_utf8, incomplete.
Use a documented deterministic classification; arbitrary unknown undecodable bytes
must not silently hide an expected text format. An explicit root symlink always uses
link_not_followed, incomplete. Every remaining error/limit status is incomplete.
Directory status is counted if complete, partial if any descendant is incomplete;
missing/failed root retains its specific status. Stable labels may explain these
statuses, but labels are not an API. Schema/status changes require versioning.

A partial token value describes successfully obtained text only; it cannot be used
as a full-file count. On interruption without a trustworthy extraction result use
null. The human >= marker means the estimate is incomplete; do not claim a formal
mathematical lower bound for BPE token counts. Totals remain estimates of known
content, not substitute full totals. Test strict exit precedence across mixed roots.

## Distribution and claims (F-16/F-17/F-18)

Use explicit sdist/wheel content allowlists and a tracked clean source export for
release artifacts. Check untracked sentinels at checkout root AND inside allowed
source/tests directories; directory-only includes do not establish exclusion. If
ordinary dirty-checkout builds cannot exclude them, fail clearly rather than package
them. Keep required code, tests/build inputs, bundled vocabulary and all licenses.
Never commit local environments, contracts, caches or generated hostile large files.

Commit hashed dependency lock(s) for supported Python/platform artifact targets.
Download with --require-hashes and record lock SHA-256, versions and target in the
manifest. Verify missing hash/tamper failure and repeated builds from identical
tracked input. Checksum files establish integrity, not origin by themselves. Prepare
separate-channel publication of the artifact digest for a later authorized release;
do not sign/tag/publish a release under this task. No broad platform artifact claim.

Correct README claims and agent examples against the installed wheel. State actual
limits, timeout behavior, supported/verified platforms, link/format exclusions,
JSON schema/strict exits and the optional DOC sandbox requirement. Profile settings
alone do not prove macro or DDE/OLE suppression. Record H-B/H-C as unverified unless
live positive-control evidence exists. Containment controls must pass regardless.

## Phase 3 — executor evidence and independent revalidation

Executor return: committed F-01..F-18 closure matrix, H-A..H-D coverage matrix,
focused regression tests, timings/RSS, effective sandbox options/mount policy,
installed-wheel agent contract examples, dependency-floor result, artifact lock and
checksums. Linux Python 3.10/3.11/3.12/3.14 runtime matrix is required; use local
environments/CI within scope, state any unavailable job explicitly. macOS/Windows
remain unverified unless actually run; no optional DOC support claim there.

Independent Claude then pins the final production SHA and reruns the affected
adversarial tests under hard outer limits, installed artifact checks and strict/JSON
consumer checks. Include a normal DOC conversion and boundary positive controls,
ZIP lying-size and XML structural cases, PDF flood/recovery, deep/mixed roots,
non-UTF-8 input, path escaping/races and dirty-checkout packaging. Mock-only tests
are insufficient for DOC containment. Preserve failed controls/unknown coverage;
no test result may be inferred from dependency metadata or unavailable runners.

Commit every completed phase and post SHA-linked gh comments; the independent
reviewer also submits a COMMENTED review with exact production/evidence SHAs.
No self-approval substitutes for independent evidence. Verify remote head before
normal pushes and API receipts afterward. Keep review conversation sanitized at
class level for native DOC effects; do not add exploit URLs/payload recipes.

Final Orc phase: adjudicate each closure on the actual fixed SHA, update living
state and disclose any remaining restrictions to the human. Unverified platform or
feature coverage must be explicit. PR stays draft until that adjudication; even a
passing review grants no merge/tag/release. No 0.1.1 backport is implemented here;
issue a separate brief if needed while 0.2.0 remains blocked.

Stop/return to Orc: unsafe/unbounded tests, isolation weakening, irreconcilable cap
regression, unrelated production drift, private-data need, sensitive released-version
vulnerability, new host/billing/access requirement or a material scope change.
Report a sanitized failure and concrete next action; do not force-push or bypass it.
