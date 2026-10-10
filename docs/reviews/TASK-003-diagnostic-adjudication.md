# TASK-003 — Orc adjudication of the exhausted DOC diagnostic

Date: 2026-10-07 (America/Sao_Paulo). Owner: ttree Orc, Codex.
Evidence: 373d19501ada3f6d507227c4e387ead226403240,
`TASK-003-diagnostic-return.md`; verified executor receipt:
https://github.com/indes-dev/ttree/pull/1#issuecomment-6043859868.

## Accepted observations and open proof

Accept the required stop at the finite 2048 MiB diagnostic AS ceiling. All three
native exports failed before producing an OLE fixture. No native import was run.
Do not infer that a larger cap is necessary or that importing an existing DOC
fails. No additional AS increase, reader replacement or production dependency is
approved. Production remains 9d420db, all findings remain open, PR stays draft.

Accept the live synthetic reduced-memory OOM observation, setsid-descendant
accounting and observed whole-scope cleanup as bounded diagnostic evidence.
Accept the aggregate CPU trigger observation only. Final CPU usage through
termination was not retained; <=250 ms termination overshoot remains unverified.
The local assertion and batch exit 0 are not full phase-1 acceptance. Native
denial, import, worker and oversized-IPC controls also remain open.

Orc checks: retained checksums passed, diagnostic shell syntax passed, production
diff was empty, and the branch/PR head and published executor receipt matched the
evidence SHA. No native diagnostic was repeated by the Orc.

## Direction

Freeze amendment 2, `TASK-003-amendment-2-base-and-native-import.md`. Test native
import directly with an existing public upstream test fixture. Fixture export is
not a runtime operation required by ttree, so it must not be the only route to
import evidence. Treat the upstream input as untrusted and keep every boundary.
The same finite diagnostic ceilings remain binding; production DOC policy still
requires Orc adjudication of actual import and containment evidence.

The Orc located Apache Tika's 32,768-byte testWORD.doc at immutable source commit
9f9b452634bac9d0e04f78b8c113cd69aee13603. A bounded metadata/download check verified
the Git blob ID, byte length, OLE signature and SHA-256. Upstream LICENSE.txt and
NOTICE.txt were inspected. This is provenance evidence only; no reader was run.
Source:
https://github.com/apache/tika/blob/9f9b452634bac9d0e04f78b8c113cd69aee13603/tika-parsers/tika-parsers-standard/tika-parsers-standard-modules/tika-parser-microsoft-module/src/test/resources/test-documents/testWORD.doc
License:
https://github.com/apache/tika/blob/9f9b452634bac9d0e04f78b8c113cd69aee13603/LICENSE.txt
Notice:
https://github.com/apache/tika/blob/9f9b452634bac9d0e04f78b8c113cd69aee13603/NOTICE.txt
Only a test input is proposed; Apache Tika/Java is not a runtime dependency.

Unblock the independent base-worker proof and DOCX/PDF/tree/agent/package fixes
after their own bounded controls pass. Quarantine the existing unsafe DOC path
while doing this. Do not claim complete DOC support or close the whole remediation
milestone while its gate remains open. DOC remains an intended capability; this
amendment does not remove it from the requested outcome or authorize release.

## Project coordination backlog

The human accepts an initial manual round trip: Eryon Retomar selects the correct
executor; the human submits the command; after its return, Eryon Retomar/Devolver
ao Orc selects the correct project Orc and the human submits the command. Use
this for a period before validating direct automatic integration. Preserve that
ttree requirement and exact role/destination evidence in project handoff/backlog.
The Orc's responsibility here is ttree; harness implementation remains with its
owner. Neither the Orc-return action nor automatic delivery is claimed to exist.
