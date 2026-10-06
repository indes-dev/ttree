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
