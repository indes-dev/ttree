# TASK-004 — Orc adjudication

Date: 2026-10-08 (America/Sao_Paulo). Owner: ttree Orc, Codex.
Production reviewed: 4382916510f91b065e45d6fdfa7b1243b174d75f.
Executor evidence: 780c9744b64efca22a31a2914177d09166528a0d.
Independent evidence: 1826300ae8d6d9ab30d09a159a21c922c388079f.
Independent phases: 7c5094b -> cd8ee5d -> 1826300.
Receipt: https://github.com/indes-dev/ttree/pull/1#issuecomment-6068191850.
COMMENTED review:
https://github.com/indes-dev/ttree/pull/1#pullrequestreview-5462304317.

## Evidence and review closure

Accept the submitted review as a bounded independent return, with material gaps.
The Orc verified all13 evidence checksums and the checksum-file digest
652d1c3cd7fc57b38411c3ceaf1c5cedad501c8410d88052de201cd939e85add;
read actual probe/suite/provenance/build/offline records, verified COMMENTED state
and commit identity, and checked production tree identity through1826300.
No passed suite or rejected control was rerun by the Orc. All review commits remain.
Phase3 did not need a new Orc instruction citingcd8ee5d: the frozen brief already
covered findings and return. Missing such a record is not an authority violation.

Close TASK-004's adjudication milestone as a review of4382916 with partial coverage.
This is review-work closure, not completion of all acceptance checks or release.
Subsequent source changes require new exact-SHA revalidation. TASK-003 stays open.

## Per-ID dispositions on the reviewed revision

| IDs | Orc disposition |
|---|---|
| F-04 | Accept dated independent correction: floor/CI and 2026-10-08T20:04:19Z advisory snapshot. No claim about future advisories. |
| F-05 | Accept independently checked strict exit mechanism/precedence. N-4 prevents full null-value/result-contract closure. |
| F-06 | Accept corrected behavior at suite-level independent evidence; no standalone probe is claimed. |
| F-13 | Accept independently verified missing-root total/completeness correction. |
| F-16/F-17 | Accept independent tracked artifact/inventory/reproducibility and hash-enforced offline controls for the measured cp312/Linuxx86_64 artifact only. New builds still need identity checks. |
| F-01 | Keep acceptance open: bounded-worker containment is present, but separate hostile PDF evidence remains incomplete. |
| F-02 | Accept independently demonstrated temporary quarantine; keep intended DOC delivery and native acceptance open. |
| F-03/F-07/F-10/F-11/F-12/F-14 | Keep independent acceptance open. Four suites passed, but blocked separate controls were not completed; preserve executor evidence at its actual scope. |
| F-08 | Keep open: N-2 contradicts the declared input envelope; independent deep-tree coverage is incomplete. |
| F-09 | Keep open: U+2028/U+2029 and literal backslash need unambiguous human rendering; JSON/native byte mapping already passed. |
| F-15 | Keep base teardown coverage and native actual-reader controls open. Diagnostic final accounting alone does not close them. |
| F-18 | Keep open: reconcile 64MiB input, unknown directory counts and rendering/platform/performance claims with measured behavior. |
| H-A | Descriptor approach exists; independent race-specific acceptance remains open. |
| H-B/H-C | Unverified. Inactive DOC avoids its exposure; macro/DDE suppression is not proved. |
| H-D | Accept Linux3.10/3.11/3.12/3.14 suite/provenance evidence only. Restricted-userns hosts, macOS/Windows remain capability/coverage gaps. |

## New findings and direction

N-1 is a release blocker, High by inspection. The worker invokes Python -m from
an inherited caller directory without isolated mode, before containment. Python's
primary documentation confirms that -m adds the current directory and that -I
excludes it/user-site and ignores Python environment variables:
https://docs.python.org/3.10/using/cmdline.html#cmdoption-I
No exploit execution or exposure in releasedv0.1.0/installedold0.2.0 is established.
Require isolated worker startup in a controlled private directory, installed-package
provenance and a harmless regression proving untrusted local modules do not run.

Accept N-2 as a correctness/cap regression: the12MiB file-size rlimit applies to
snapshot storage as well as response. Separate the finite storage/output bounds;
retain64MiB input and actual12MiB IPC, without raising AS/CPU/wall limits.
Accept N-4: incomplete unknown directory values must be null, while genuine known
zero remains zero. Preserve sums of known contributions and strict completeness.

N-3 is a measured throughput gap, not a fixed630-entry ceiling.40 files took7.592s;
632 is extrapolated for that environment/input. Keep120s deadline and fresh isolation.
Authorize bounded benign profiling and evidence-backed local improvements only;
new persistent pool/batching/cross-file-state architecture needs a proved design and
Orc instruction. State remaining performance limits instead of hiding truncation.

N-5 is an explicit fail-closed portability gap. Keep namespaces mandatory in this
batch; no unsafe fallback/sysctl/host install. Document supported/verified runtime
and recovery on a Linux host with the required primitives. No universal-platform or
restricted-host outcome is silently accepted as delivered.

Issue TASK-003 amendment3 for these base corrections and a separate single native
1024MiBAS observation. Maintain all aggregate controls, no adapter enablement. A
low sampled VmPeak does not exclude a denied larger reservation; sampling gaps and
mixed-error causes remain hypotheses. No blind cap increase or guessed root cause.

## Blocked coverage and release boundary

The reviewer reports classifier-blocked separate controls and a human choice not
to retry them. Preserve that stop. Do not transfer the same blocked action to
another provider/session just to evade the denial, lower safeguards or manufacture
independence from executor evidence. Ordinary safe new-fix regressions may proceed
within their grant. If a control is denied, retain denial and return the gap.
Orc must arrange an authorized independent validation route before closing these
acceptance items; that route is not created by this adjudication.

PR remains OPEN/DRAFT. Original TASK-003 progress0/4/nativephase1 stays open;
base candidate substages and accepted limited corrections are recorded separately.
No merge/tag/release, installed CLI change, new dependency/reader/host package,
privileged/persistent setting, model/billing change, other-project work or backport.
