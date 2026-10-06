# TASK-003 — execution handoff

Date: 2026-10-06 UTC. Owner: ttree project Orc, Codex.
The human requested continuation through the existing harness. This coordination
stage preserves the frozen fix brief and the public cross-review history.

Technical scope remains TASK-003-remediation-brief.md at
ee4629b1aee910cdc5c13033327b11019f273447. Production remains the unfixed 9d420db
candidate. All F-01..F-18 need remediation; H-A..H-D retain unverified coverage.

Prepare a fresh implementation executor on the host that owns the repository.
Keep the Orc and independent reviewer separate. Do not resume the Orc as the
implementation executor. A continuation checkpoint records completed evidence,
the bounded prototype as the first action, stop conditions and the new-session
destination. Checkpoint creation is not executor dispatch or launch authorization.

Progress milestones: prototype; focused corrections; executor evidence plus
independent fixed-SHA revalidation; final Orc adjudication. This maps the frozen
brief's three numbered phases plus final Orc stage without changing its scope.
The review task is complete; its findings are still open in the remediation task.
Earlier implementation/release preparation remains incomplete until acceptance.

Each completed phase must still add substantive commits and communicate through
gh. Checkpoint/progress metadata must reflect observed execution, not a submitted
prompt or a tool's success message. This documentation stage runs no implementation
test, changes no production code and closes no security finding.

Keep PR #1 OPEN/DRAFT. No merge/tag/release, host-package installation, unrelated
project change or local CLI install is granted. Current public v0.1.0 hardening
route remains https://github.com/indes-dev/ttree/issues/2.
