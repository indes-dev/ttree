# TASK-002 Orc record

This is an append-only public record. Keep private operating documents and private
validation data out of this repository. Each new stage must use a new commit.

## 2026-10-06 — Review preparation

Author: project Orc, using Codex. Human instruction: prepare independent Claude
cross-validation for safe open-source development and use by agents; record stages
with commits and communicate the cross-review through GitHub CLI.

Public base: `0f1d6bbd9dbb02ebc91dd0180ec4f81c09bbb361` (`v0.1.0`).
Candidate implementation: `9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e` (`0.2.0`).
Branch: `task-001-office-pdf`. No merge or release is authorized by this review brief.

The candidate adds local DOCX/PDF text extraction, optional LibreOffice DOC reading,
token-only default display and a bundled verified vocabulary. The executor reported
15 passing tests and a fresh Linux x86_64 / CPython 3.12 offline installation under
OS-level network blocking. These are prior evidence, not independent validation.

Accepted dependency rationale: replace Gigatoken with tiktoken while retaining the
same o200k_base vocabulary. On the inspected environment, the tokenizer dependency
chain fell from 13 distributions / 84,636,160 installed file bytes to 7 distributions /
8,878,042 bytes. PDF adds pypdf. DOCX uses the Python standard library. DOC requires an
optional local reader. This rationale and the measurements require independent review.
Literal strings resembling special tokens now count as ordinary document content.

The review must examine resource bounds, unintended effects and ambiguous results
for agent consumers. No security or cross-platform acceptance is claimed yet.
The issued scope is `docs/reviews/TASK-002-cross-validation.md`.
Claude execution, verdict, fixes and final release adjudication remain pending.

The current handoff publishes the candidate as a draft PR and posts a sanitized
review request using `gh`. GitHub postconditions will be recorded in a later commit
after the actual PR and comment are observed. Do not treat this entry as dispatch
or review completion.

## 2026-10-06T15:29:58Z — GitHub handoff verified

Author: project Orc, using Codex.

The implementation and brief commits were pushed without rewriting history.
GitHub reports draft PR [#1](https://github.com/indes-dev/ttree/pull/1), targeting
`main`, with head `ac3c322b602dd47084814ff8b94b756936575c10` at this checkpoint.
The observed public main SHA remains `0f1d6bbd9dbb02ebc91dd0180ec4f81c09bbb361`.

The review request was posted through `gh pr comment --body-file` and retrieved
through the GitHub API. Its observed timestamp is `2026-10-06T15:29:36Z`.
Receipt: [handoff comment](https://github.com/indes-dev/ttree/pull/1#issuecomment-6019648964).
Its exact public text is preserved in `TASK-002-gh-handoff.md`.

The project Orc reconciled the project record to the implemented candidate and
pending independent review, accepted the measured dependency rationale, and issued
the bounded review capability and frozen brief. Private governance remains outside
this repository. The public technical direction and phase contract are committed here.

Claude inference was not invoked. Preflight, independent validation, findings,
adjudication, any fixes and release remain pending. Next actor: independent Claude
reviewer after the applicable execution bootstrap and recorded dispatch.
This is a verified communication handoff, not a completed cross-review.

## 2026-10-06 — Phase 4 adjudication

Author: project Orc, Codex. Independent Claude review returned at findings head
`bac3684ea3fa36b44e5db8b124c97d14f65374ab`. The branch was fast-forwarded from the
previous coordination head; the reviewed production implementation remains `9d420db`.
GitHub review and OPEN/DRAFT PR state were verified against the actual repository.

All F-01 through F-18 are accepted for remediation, with remedy choices recorded in
TASK-002-orc-adjudication.md. Three High findings block release. None is fixed by this
documentation stage. H-A through H-D retain explicit unverified coverage.
The public issue body records class-level v0.1.0 hardening/disclosure direction.
Observed OPEN receipt: https://github.com/indes-dev/ttree/issues/2. The retrieved
issue body matches TASK-002-public-hardening-issue.md.
The next stage freezes TASK-003, then delegates implementation and independent
SHA-specific revalidation. No source change or release action is authorized here.
