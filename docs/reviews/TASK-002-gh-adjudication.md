TASK-002 phase 4 — Orc adjudication of the independent Claude review.

0.2.0 is not release-ready. All F-01 through F-18 are accepted for remediation;
the three High findings block release. H-A through H-D remain explicitly unverified.
This stage changes documentation only; no finding is closed by this commit.

Adjudication commit: 8a6f563fa01d9b2ced60832b9784cabd30280d8c
https://github.com/indes-dev/ttree/blob/8a6f563fa01d9b2ced60832b9784cabd30280d8c/docs/reviews/TASK-002-orc-adjudication.md

Direction: bounded parsing/workers; isolated optional native DOC reading with no
unsandboxed fallback; actual DOCX decompression limits; updated parser floor;
--strict and --json with a stable completeness contract. The basic DOCX/PDF path
keeps its current minimal Python dependency model. Signature/filter checks alone
do not establish containment of native-reader effects.

Released v0.1.0 F-08/F-09: public hardening issue #2, class-level disclosure and
mitigations. No High finding has been established in v0.1.0; no emergency withdrawal
or CVE request on this evidence. If the candidate stays blocked, issue a separate
backport brief. https://github.com/indes-dev/ttree/issues/2

Next: freeze TASK-003 for an implementation Agent, then independent Claude
SHA-specific revalidation and final Orc closure. Keep this PR draft. No merge,
tag or release is authorized. Preserve the review and correction stage commits.
