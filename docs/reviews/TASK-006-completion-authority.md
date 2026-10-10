# Decision 0015: Integrated completion and merge to main

Status: accepted. Date: 2026-10-10 (America/Sao_Paulo). Owner: ttree Orc.
Source: Zak explicitly requests Orc+Agent execution in this session and the changed
function in main with no pending implementation or review work. This supersedes
0013/0014's prohibition on new implementation and main merge, and their mandatory
handoff to another executor. Preserve all historical briefs and reports unchanged.

## Outcome and authority

Deliver local DOC, DOCX and text-PDF estimates, strict JSON and safe bounded runs
for users and agents. Implement, inspect, test, record commits and communicate on
PR1, then merge the validated result into main. This session performs both roles;
its new checks are executor/Orc checks, not a new independent Claude approval.
Use existing independent evidence for unchanged code. Do not require Zak to relay
technical findings or commission another unavailable adversarial analysis.

## Bounded engineering direction

Replace the failed optional native converter with static Word binary text reading.
Use maintained small Python OLE parsing and Microsoft's published piece-table
specification. Do not activate LibreOffice, macros, DDE, OLE objects or external
links. Keep all parsing inside finite workers. Minimize dependencies by avoiding
native programs; measure and document the necessary small OLE dependency.
Address remaining low notes and restricted-Linux worker operation without an
unsandboxed fallback. Inspect throughput and distinguish finite scan budgets from
an actual entry-count defect. Support the project's Linux target; do not claim
untested Windows/macOS capability. Validate normal DOC fixtures, all existing
regressions, installed artifacts, reproduction, offline installation and CI.

## Safety and completion

Do not recreate previously runtime-denied hostile fixtures or route them to
another session/provider. Preserve their exact historical independent-coverage
labels. A static reader changes the native attack surface; inspect that design
and its actual limits rather than claiming old native tests passed. No secrets,
private contracts, privileged/system changes, harness changes or new services.
No tag or package-registry publication is requested. Before merging, communicate
material supported-format/platform/resource restrictions and recovery to Zak.
Use a normal merge with exact-head verification and successful required checks.
Rollback is a normal revert on main, not rewritten history. Do not claim closure
before main contains the tested functionality and project records reflect it.
