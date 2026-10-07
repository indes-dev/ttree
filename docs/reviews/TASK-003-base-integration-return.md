# TASK-003 — base integration and agent results

Amendment 2 continuation after base proof 3dfbb9d. Overall remains **0/4** because
the native gate is open. Candidate source only; installed CLI/release unchanged.

This stage wires the proved resource envelope into document/text workers, removes
all native DOC conversion/fallback code, and implements descriptor-relative
no-follow scanning and iterative aggregation/rendering. JSON follows the frozen
schema: `path` and POSIX `path_bytes_base64` in both roots and flat entries; entry
`.` represents the root. Unknown counts are null, known bytes survive failures,
and directories/total aggregate only known values. Strict precedence is 2/1/3/0.
Display flags do not discard JSON entries. Human controls, format characters and
surrogates are escaped; parser details are never forwarded. BOM UTF-16/32 decoding
precedes binary classification. The documented binary/media suffix exclusions are
complete; unsupported text-bearing formats and unknown undecodable data are not.

Relevant candidate coverage: F-01/F-03/F-05/F-06/F-07/F-08/F-09/F-12/F-13/F-14/F-15,
H-A (some document semantics and artifact validation still pending). F-02 remains
open: inactive DOC is explicit `unsupported`, null tokens and incomplete, preserving
known bytes. This is quarantine under amendment 2, not delivery of optional DOC.
No finding is self-closed; independent exact-SHA review and Orc closure remain.

22 real-behavior tests passed on Linux/Python 3.12.14 in 10.767 s:
`TMPDIR=$PWD/.tmp .venv/bin/python -m unittest discover -s tests -v`.
Log: `review/task-003/evidence/base-integration/tests.log` (checksummed).
Tests include actual worker tokenization, mixed roots and strict precedence;
null/no-text/encoding classifications; raw byte filename roundtrip and human
escaping; symlink roots/ancestors/descendants; finite configuration and entry cap;
1,100-level directory traversal, JSON and human rendering; real 1 s scan deadline
interrupting a PDF operator flood and retaining the later root; live file and
directory replacement races against only disposable outside sentinels; unreadable
file bytes; real kernel-denied unshare failing closed. Two IPC/cleanup controls
substitute only the worker entrypoint while launching real bounded subprocesses:
an actual >12 MiB writer is rejected, and an observed setsid child is dead after
the production pidfd termination barrier. No mocked extraction or availability.

Next independent base stage: supported AlternateContent branch, moved/deleted
text, strict namespace/formatting and notes; PDF warning/cipher cases; pypdf floor
and current advisory evidence; exact distribution allowlists, hash-locked offline
artifact, dirty checkout sentinels, repeated tracked builds and installed-wheel
runtime matrix. Native final accounting/direct fixture import proceeds separately.
