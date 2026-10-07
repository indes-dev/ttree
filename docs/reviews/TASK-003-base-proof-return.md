# TASK-003 amendment 2 — independent base proof

Executor: Codex, PROJECT / AGENT, indes-front. Authority: amendment 2 pinned at
c475f28cd7c0b0766d450b7cdf0335099984349d; original basic-file envelope unchanged.
Overall milestones remain **0/4**: native import/final CPU/containment acceptance
is open. This is a passing **unwired base feasibility substage**, not release or
per-finding closure. Production and the installed CLI were unchanged by this stage.

## Candidate and actual observations

`review/task-003/base_worker.py` processes DOCX/PDF/plain text and tokenizes inside
fresh Linux workers: 15 s wall, 10 s CPU, 512 MiB address space. There is no native
reader invocation or new host command dependency. A private snapshot comes from
an already-open no-follow descriptor; input cap 64 MiB. XML reads are incremental,
with actual 4 MiB/part and 8 MiB/selected-parts caps, depth 128, 100,000 elements,
4,096 ZIP members and 1,000,000 extracted characters. PDF page cap is 2,000.
Resource caps bound parser allocations before a content-level cap can be checked.

The coordinator reads IPC incrementally and rejects the **actual 12 MiB + 1st
byte**, without buffering an unlimited response. A separate control pipe carries
only namespace PID 1's host identity. Kernel PID namespace teardown includes
forked/reparented/setsid descendants; a pidfd provides a termination barrier before
return. User/PID namespaces and pidfds are mandatory here; unavailable primitives
fail closed. This does not claim filesystem or network sandboxing for base parsers.

The final synthetic batch passed all 18 assertions in 22.7408 s:

- DOCX `Readable DOCX text`: 4 tokens; PDF `Readable PDF text`: 3 tokens.
- Actual expanded XML reads stopped at 4,194,305 and 8,388,609 bytes; malformed
  ZIP metadata (both local/central declared size 32) was rejected by CRC validation.
  The latter case does **not** claim 5 MiB was delivered by ZipExtFile: it rejects
  the inconsistent archive; the honest-size bomb independently proves actual caps.
- Depth 129 and element 100,001 were rejected; malformed ZIP returned fixed failure.
- Damaged PDF retained known text and marked partial from counted parser warnings,
  without formatting/forwarding parser messages. Shared operator flood stayed bounded.
- A real excessive writer, timeout, exit-7 worker, 600 MiB allocation attempt and
  CPU loop tested IPC/wall/AS/CPU boundaries. The CPU loop died in its fresh 10 s
  envelope; later workers were not charged against that earlier worker's allowance.
- The live setsid child was identified externally by namespace PID, host PID,
  starttime, session and namespace inode. It had no live survivor after the pidfd
  barrier. The initial test found an asynchronous teardown race; the revised
  candidate waits for namespace teardown. Failed diagnostic scratch is retained.
- A normal file and a separate normal root counted successfully after hostile
  cases. This is coordinator continuation proof, **not yet production tree scanning**.

## Reproduction and evidence

Actual command: `timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0
.venv/bin/python review/task-003/prove_base.py .tmp/base-proof-3` (exit 0).
Equivalent bounded wrapper: `bash review/task-003/run_base_proof.sh .tmp/FRESH`.
Python 3.12.14; kernel 7.2.8-arch1-2; pypdf 6.19.0; tiktoken 0.14.0.
Small public evidence: `review/task-003/evidence/amendment-2-base/results.json`,
plus SHA256SUMS. Synthetic fixtures/oversized output are not committed or packaged.

Pending: production no-follow tree traversal/deadline; complete result schema,
strict precedence, escaping, DOC quarantine; full DOCX semantic regressions and
PDF correctness; dependency advisory/floor and artifact/runtime matrix; native
stream; independent Claude exact-fixed-SHA review; Orc per-ID adjudication.
Amendment 2 authorizes continuation of these base stages without another gate.
