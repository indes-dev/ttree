# TASK-005: Orc adjudication and correction sprint closure

Status: issued and frozen, 2026-10-10. Owner: ttree Orc, Codex.
**Close the bounded amendment-3 correction/review sprint. TASK-005 is done 4/4.**
**Deployment/release of the full requested upgrade remains NO-GO.**
Do not reopen the completed executor or reviewer batch merely for a phase boundary
or the low notes below. No new implementation or review task is issued here.

## Evidence and exact acceptance scope

Production/runtime/tests/build: 4c07f5a06a80a02002dbfecc73331be6886d0180.
Executor evidence: cae2000fbaa143aff904d84545b85395951f3777.
Independent evidence: ef7564effb432cb86059fd78f3c8bfb8197da0ae (includes preflight
dc0e6f6 and findings6712a75). The ef7564e addition completes the H-2 note referenced
prematurely in6712a75; retain both historical commits, adjudicate the final report.
Review: https://github.com/indes-dev/ttree/pull/1#pullrequestreview-5475369310.
Receipt: https://github.com/indes-dev/ttree/pull/1#issuecomment-6089274350.

Orc verified12 evidence checksums, checksum-list digest
 a3ec8f1ab6cc0de7a9206cee4f4d349299f573332fd606dbe779bb50100aa41e,
actual API review/receipt identity and pins, four5/5 regression logs, live deadline/
null/quarantine/exit records, offline control results, retained rebuild products
and unchanged production tree. Current PR checks are successful. No new suite,
denied hostile fixture, vulnerable bootstrap or native operation was run by Orc.

Wheel SHA256:926c0af25050cbad17b2305c21f0e39f0deb4fcaef14fc5d460861bab53e6e1b.
Sdist SHA256:83a658cc0a8de6f7fade3dea54ecdd9cd24bea5e550fda5799ecc7164843ad86.
Build metadata SHA256:a81534494e3a5480a0d80c6e5f3f3aef64cba3cf28ce5f469b55060d931c0271.
Offline checksum-list SHA256:e872bab11fd69a6fae9c194b86ca4e7c2c2a8789c376392e506d4162e23a19a2.
Artifact acceptance is CPython3.12/Linuxx86_64. The five new installed-wheel
regressions passed independently on Linux3.10/3.11/3.12/3.14; this is not a claim
that every Python minor or other platform was tested.

## Adjudicated items

| IDs | Orc disposition at exact production/artifact |
| --- | --- |
| N-1 | Close the worker/caller-module defect: independent installed-console benign marker regression and source inspection verify -I/private cwd/provenance. Do not extend this to arbitrary Python parent bootstrap or old released/installed versions. |
| N-2 | Close the snapshot-versus-response defect: benign11/13/64MiB, over-input/lowered-input/response and following-root behavior verified independently. This does not close hostile ZIP expansion coverage. |
| N-4 / F-05 | Close unknown/null aggregation and strict exit-contract defects at tested scope. Unknown-only fields remain null; genuine zero/known sums remain distinct. Live precedence1>3>0 and real-clock deadline1.043s for a1s setting passed. No exact hard realtime timing guarantee is inferred. |
| F-08 | Accept independently verified large-file correction. Keep deep-tree independent coverage open. |
| F-09 | Close the human escaping residuals at tested scope; literal backslash/line separators are unambiguous, JSON native paths preserved. |
| F-18 | Accept the three prior README residual corrections with D-1/D-2 low notes retained below. No universal host/performance claim. |
| F-04 | Accept dated independent floor/advisory observation2026-10-09T20:58:37Z,0/51 affecting6.19.0. This is not future advisory assurance. |
| F-06 | Carry forward TASK-004 suite-level acceptance for unchanged code. Not newly executed here. |
| F-13 | Accept new live multi-root incomplete total verification. |
| F-16 / F-17 | Accept exact new artifact rebuild/inventory and hash-enforced offline installation verification, including tamper/missing-hash failures and network namespace, at measured target scope. |
| F-01 | Temporary bounded-worker containment; separate hostile PDF acceptance open. |
| F-02 | Quarantine independently reverified; native DOC remains capability not delivered. |
| F-03 / F-07 / F-10 / F-11 / F-12 / F-14 / base-F-15 / H-A | Prior separate independent controls remain unverified. No recreation, runtime/session/provider reroute or false closure of denied controls. |
| Native F-15 / H-B / H-C | DOC inactive; actual native capability and controls remain undelivered/unverified. No native success inferred from cleanup proof. |
| H-D / N-5 | Four named Linux runtimes verified at regression scope. Restricted namespace/pidfd hosts and macOS/Windows remain unmet/unverified. |
| N-3 | Throughput capability gap retained: approximately530–590 tinyfiles/120s is a local linear projection, not a fixed cap. Live final-wheel40-file control8.121s corroborates scale. Subtree selection is a current workaround. |

## Low notes and native diagnostic

D-1: retain a low documentation follow-up to describe the effective response limit,
not only its12MiB default. Actual lower-limit enforcement is verified and is not
weakened by the wording. D-2: label provisional-wheel profiling precisely; independent
final-wheel40-file control corroborates order of magnitude, not byte equality or an
identical timing benchmark. H-1: unused counter is hygiene. H-2: build extraction
filter is hardening of the controlled self-built-sdist path. This acceptance does
not authorize accepting arbitrary untrusted tar input. All four stay in backlog;
none warrants reopening the completed bounded sprint or a new blocking fix loop.
No production/build/docs fix is performed in this adjudication.

Native read-only evidence: VmPeak/VmSize reached1024MiB, while charged cgroup peak
was796319744 of805306368 bytes (about98.9%). Two ceilings were near their limits;
page cache may contribute to cgroup memory. Accept pressure as a supported hypothesis,
not a unique root cause or proof of resident-memory exhaustion. One grant remains
consumed. No retry/cap increase/new reader/mount/tool/adapter enablement is authorized.

## Remaining outcome and ownership

The sprint and TASK-005 review are complete at their issued scope. Original
TASK-003 remains paused/open0/4 under its native milestone rule; the accepted base
substage is complete and is not erased by that original milestone display.
Missing DOC and independent safety coverage prevent GO for the requested full upgrade.
A narrower release or a waiver is not inferred. No merge/tag/release/install is granted.

Next actor is ttree Orc, not the completed executor/reviewer. Own the remaining
safety-coverage/native/throughput/portability disposition and prepare a concrete
bounded proposal before any new grant. Retain prior classifier-denied controls and
human choice not to repeat them; do not route the same denied actions elsewhere.
Changes to requested delivery/scope require applicable human direction. Native
retry, architecture, privileges, costs or platforms are not expanded by sprint closure.
No new task, runtime/job, user CLI, host/harness or release change occurs here.
