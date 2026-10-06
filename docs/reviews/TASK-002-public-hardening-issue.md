Released v0.1.0 has two input-handling weaknesses confirmed by independent review:

- Deep directory trees or very large plain-text files can abort the whole scan and lose results for other roots/siblings.
- Names, link targets and root paths can contain terminal controls or line breaks that reach human output without escaping.

These are public hardening items of low impact in the released version. The three
High findings against the unreleased 0.2.0 candidate have not been established in
v0.1.0. No disclosure of secrets or document contents was observed.

Until corrected, prefer controlled directory trees and treat human tree output as
presentation rather than an authoritative machine interface. An outer process
resource/time limit can contain a failed scan; it does not repair missing results.

Acceptance: bounded file reads, iterative traversal/rendering/aggregation, continued
results after per-entry errors, and escaping on every filename/link/root surface.
Add a stable completeness/JSON contract to the candidate for agent consumers.

Track the candidate fixes in draft PR #1 and the committed TASK-002 Orc adjudication.
If 0.2.0 remains blocked, prepare a separate v0.1.1 backport brief for these two
released-code fixes. This issue does not authorize a merge, tag or release.
No emergency withdrawal or CVE request is initiated on the current evidence.

Review: https://github.com/indes-dev/ttree/pull/1#pullrequestreview-5431309247
