# TASK-003 amendment 3: Orc adjudication and deployment verdict

Status: issued and frozen, 2026-10-09. Owner: ttree Orc, Codex.
Verdict: **NO-GO for deployment/release of the requested upgrade.**
Accept the amendment-3 executor batch as complete at its granted scope. Do not
resume that batch or repeat its consumed native observation. This acceptance does
not close findings independently or change the requested DOC outcome.

## Verified delivery

Production/build/test: 4c07f5a06a80a02002dbfecc73331be6886d0180.
Executor evidence: cae2000fbaa143aff904d84545b85395951f3777.
Return: https://github.com/indes-dev/ttree/pull/1#issuecomment-6084744354.
Orc verified the exact API receipt body, all 43 files in four evidence checksum
sets, 14 offline checksum entries, wheel/sdist/list digests, all eight installed
module hashes in each of four environments, production/evidence tree equality,
clean local/remote/PR head and ten successful final-head CI jobs (PR plus push).
Recorded suites pass 37 tests on Linux Python 3.10/3.11/3.12/3.14. These are executor
and CI results; Orc integrity inspection is not a new independent Claude review.

Wheel SHA256: 926c0af25050cbad17b2305c21f0e39f0deb4fcaef14fc5d460861bab53e6e1b.
Sdist SHA256: 83a658cc0a8de6f7fade3dea54ecdd9cd24bea5e550fda5799ecc7164843ad86.
Offline SHA256SUMS digest: e872bab11fd69a6fae9c194b86ca4e7c2c2a8789c376392e506d4162e23a19a2.
Artifact target: CPython 3.12 / Linux x86_64 only.

## Disposition

| Item | Orc disposition |
| --- | --- |
| N-1 | Isolated bootstrap/private cwd and harmless fixed-wheel regression delivered. Correction candidate; exact-new-SHA independent verification required. No pre-fix exploit or released-version exposure inferred. |
| N-2 / F-08 | Separate finite snapshot and IPC/output caps delivered with benign 11/13/64 MiB and continuation evidence. Correction candidate; independent changed-code verification required. |
| N-4 / F-05 | Fieldwise null/known-zero aggregation delivered with JSON/human regressions. Correction candidate; independent contract verification required. |
| F-09 / F-18 | Backslash/line-separator escape and measured claims delivered. Correction candidate; independent changed-code verification required. |
| N-3 | Bounded profiling delivered; throughput capability gap remains. Forty tiny files took 9.049 s. About 530 similar files/120 s is a local projection, not a fixed cap. Smaller subtrees are a workaround. No architecture optimization is approved here. |
| N-5 / H-D | Mandatory Linux namespace/pidfd boundary retained. Restricted hosts and non-Linux capability remain unmet/unverified. No weaker fallback is accepted. |
| Native DOC / F-02 / F-15 / H-B / H-C | Single observation consumed and properly returned as failed. DOC remains unsupported/null/incomplete; intended delivery and actual-reader controls remain open. |
| Other F/H IDs | Preserve the exact scopes in decision 0012 and TASK-004 adjudication. Previously denied separate independent controls remain unverified. Old review of 4382916 does not approve changed 4c07f5a or new artifact bytes. |

Native observation: exit 139/std::bad_alloc, no text, 212 actual-reader samples,
VmPeak/VmSize maximum 1,048,576 KiB. Consistent with virtual-space pressure; not
unique proof. Retained final CPU 3.169217 s, OOM kills zero, empty membership and
cleanup reported and internally consistent. Accept diagnostic grant completion,
not native import success. No retry, raised limits, new tool/reader/mount or adapter
enablement is authorized. Base corrections were correctly completed despite failure.

## Next action and release boundary

Issue TASK-005 for independent review of the changed code/artifact using the
existing distinct Claude reviewer. Focus on harmless newly delivered regressions,
installed provenance, new artifact identity/reproduction and changed README claims.
Do not reroute/retry previously classifier-denied actions or claim their closure.
Keep their coverage gaps explicit, even if all new regressions pass.

The Orc owns collection and final adjudication. Review completion cannot grant
release, accept DOC removal as the requested full outcome or waive safety coverage.
Any proposed narrower release must clearly state DOC, throughput and host limits
and obtain the applicable direction/authority; no such release is approved here.
Original TASK-003 stays open at 0/4 under its native milestone rule. TASK-004 remains
closed with partial coverage. No production changes, native execution, CLI install,
merge, tag, release, host/harness change or reviewer runtime dispatch by this stage.
