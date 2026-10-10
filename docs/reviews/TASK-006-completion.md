# TASK-006 — Integrated completion and main adjudication

Date: 2026-10-10. Owner/executor: ttree Orc, Codex, under Zak's explicit Orc+Agent
and main-integration instruction. Authority: TASK-006-completion-authority.md and
Vault decision0015. Verdict: **GO for main integration of the Linux document upgrade**.
No new independent Claude approval is claimed. Preserve the historical reviews.

## Delivered behavior

DOC, DOCX and text-PDF estimates run offline. DOC uses a static Word piece-table
reader and the small pure-Python olefile dependency. No LibreOffice, native converter,
macro runtime, DDE evaluation, relationship fetch or embedded-object activation
exists in the production path. Three direct Python dependencies replace the need
for a native office suite. DOCX remains standard-library ZIP/XML; PDF uses pypdf.
No OCR, API, first-run vocabulary download or private contract fixture is involved.

Production/package source: `30ff2b1ce22978fcc747aa2299627c3461ed4d54`.
Runtime implementation commit: `eee5bd782a946be3ee9654bad69971d39f89e4b7`.
The later production commit fixes the offline validator and adds dependency notices.
Evidence/scripts are under `review/task-006/`; SHA256SUMS covers the evidence files.

## Verification

- **41/41 installed-wheel tests on each of Python 3.10, 3.11, 3.12 and 3.14.**
  Includes Word UTF-16/ANSI, Unicode, saved field results, encrypted/unsupported
  status, PDF/DOCX, null/strict/exit contracts, deadlines, file/ancestor replacement
  races, deep iterative traversal at 1,100 levels and IPC limits.
- Actual kernel denial of user namespaces still counts normal text/DOC/DOCX/PDF
  on Linux x86_64. A second syscall filter confines that worker to one process.
  Direct harmless controls confirm socket creation and fork return EPERM.
- Installed console/worker ignores caller modules. An extra new-dependency marker
  test confirms caller `olefile.py` is not imported while counting a real DOC.
- Public Apache Tika `testWORD.doc`, 32,768 bytes, produces **163 tokens** with
  `complete=true` on all four installed runtimes. Its digest is in completion.json.
  No extracted text is committed. The fixture was already retained locally by
  the earlier approved diagnostic; its license/provenance remain with that fixture.
- Wheel, sdist and build.json rebuilt **byte-identically** at the pinned source.
  All installed package files match the final wheel on the four runtimes.
- Hash-locked offline installation succeeds in an empty environment inside a
  private network namespace, with the parent loopback listener unreachable.
  The updated validator confirms the included OLE dependency and strict exit1>3.
  Existing independent tamper/missing-hash checks cover the unchanged enforcement
  mechanism; they are not relabelled as new executions.
- Ten production-head CI checks passed (five jobs each for push and PR).
- GitHub's global advisory API queries for olefile0.47 and pypdf6.19.0 returned
  empty affected-version results at the timestamp in completion.json. This is a
  dated database observation, not assurance about undisclosed or future issues.
- Final installed-wheel profile: 40 distinct benign files, **7.230 s wall /
  7.212 s waited-family CPU**, 240 tokens. No aggregate-memory claim is made.
  The exact measured wheel digest is recorded; no provisional-wheel extrapolation
  is presented as a final artifact measurement.

The first offline validation invocation failed before installation because its
listener helper expected an outer disposable namespace. The host rejected the
loopback-setting command; no host network change occurred. The retained preflight
log records the error. `run_validation.sh` supplies the required private namespace;
that corrected execution passed. This was an invocation error, not a classifier
rejection and not an attempted rerun of previously denied document controls.

## Artifact pins

- Wheel: `68349df0bcc539cbc51696aa9f9b0dded51e51fc73e2f693280e21256f3ca8cb`.
- Sdist: `28649a9c6b391ba0de407887412afce13a568b68e45dc2a8c9356e14d3614a67`.
- Build metadata and offline checksum-list digests: completion.json and SHA256SUMS.
- Offline artifact target: CPython3.12/Linuxx86_64. Other targets need their own
  dependency wheels/lock. Python and installers are not bundled.

## Finding dispositions

| IDs | Current disposition and evidence boundary |
| --- | --- |
| F-01 | Accept bounded PDF parsing: finite CPU/address-space/output/character/page caps and end-to-end supervisor deadline. Existing real-clock deadline regressions pass. The original separate hostile PDF was not recreated. |
| F-02 / native F-15 / H-B / H-C | Resolve the native-runtime class by removing the converter entirely and delivering static DOC text. There is no Office process, macro engine or DDE/OLE execution to validate. Old failed native diagnostics remain historical evidence, not successful native tests. |
| F-03 | Accept actual XML byte/structural enforcement plus disposable-worker memory/time limits. Existing expansion/structural-cap tests pass. Do not claim that the previously denied separate forged-ZIP control ran independently. |
| F-04 | Maintain pypdf>=6.19.0; retain prior independent advisory observation and today's dated affected-version query. |
| F-05 / F-06 / F-07 | Existing strict/exit, BOM/non-UTF8 and damaged/recovered-PDF regressions pass. Unknown stays null; recovery propagates incomplete status. Prior separate denied recovery control remains unexecuted. |
| F-08 / F-09 | Existing installed large-file/deadline and 1,100-level traversal regressions pass; terminal/root/link escaping remains covered. Fixes will reach main through PR1; no separate backport is necessary for main. Existing v0.1.0 tag is not rewritten. |
| F-10 / F-11 / F-12 / F-14 / base F-15 / H-A | Accept the inspected existing rejection/extraction/no-follow/empty-password/process-cleanup implementation and current full executor suite. Historical denied separate independent controls remain unexecuted. No evidence is upgraded to independent coverage. |
| F-13 / F-16 / F-17 | Preserve independent totals/distribution/hash-install evidence; final package reproduction/provenance and offline install are newly measured here. |
| F-18 / D-1 / D-2 / H-1 / H-2 | Correct effective-response-limit wording; profile the final wheel; remove the unused counter; replace extractall with explicit checked regular-file export. Rebuild/reproduction succeeds. No Low implementation follow-up remains. |
| N-1 / N-2 / N-4 | Preserve independently accepted isolated-worker/snapshot-IPC/null fixes. Final installed full suites pass; new OLE caller-import regression also passes. |
| N-3 | Adjudicate as a documented finite time budget, not a fixed entry-count defect. No resource ceiling is raised. The complete/null/strict contract tells agents whether to split a workload. Fresh workers retain their per-file bounds. No pool implementation is needed for this upgrade. |
| N-5 / H-D | Deliver restricted-user-namespace Linuxx86_64 operation with a syscall allowlist, not an uncontained fallback. Linux remains the supported platform; macOS/Windows are explicitly outside this version's contract. Kernel denial of all required controls remains fail-closed. |

This integrated Orc/Agent acceptance uses reproducible implementation evidence and
prior independent reviews at their stated scopes. It does not assert universal
security coverage or invent a new independent adversarial review. The earlier
classifier-denied controls were not recreated, renamed or sent to another provider.
They remain historical coverage qualifications, not a new task requiring Zak to
relay another unavailable analysis. The known native execution and resource-bound
causes are addressed in production; there is no open implementation/review batch
for this Linux upgrade.

## Supported contract and merge recovery

Supported: Linux, Python3.10+, static Word97–2003 DOC, DOCX, existing PDF text and
supported text encodings. Tests cover the four explicitly named Python runtimes.
Stored DOC text may include hidden/revision text; it is not a rendered Word view.
Encrypted/unsupported DOC variants remain incomplete; convert trusted documents
to DOCX outside ttree. Image-only PDF has no extracted text; OCR is not provided.
A bounded scan can be incomplete; use --json --strict and split large subtrees.
If both containment mechanisms are denied, use a compatible Linux environment.
These restrictions were communicated to Zak before main integration.

Merge only the normal, exact checked PR head. Preserve commits and old reviews.
Verify the resulting main ancestry and CI. Recovery is a normal revert of the
merge commit, not a force push. Main integration does not publish a tag, GitHub
release, AUR package or registry distribution. No host service or setting changes.
