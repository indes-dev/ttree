# TASK-003 amendment 3: base corrections candidate

N-1 isolated startup is retained. N-2/F08 separates finite 64 MiB snapshot storage
from incrementally bounded 12 MiB IPC; after copying, worker file output gets the
response ceiling. Extraction/tokenization stay inside fresh 512 MiB AS/10 s CPU/
15 s wall workers and the 120 s scan deadline. A benign stored-padding DOCX test
counts 11/13/exactly64 MiB as 4 tokens each;64 MiB+1 rejects; the following root
still counts4. Lowered response512 B accepts13 MiB, lowered input12 MiB rejects it.
Existing real oversized-IPC and whole-tree teardown tests remain in the suite.

N-4/F05/F18 preserves unknown values independently for tokens and bytes. Failed
unenumerated directories remain null in entries/roots/totals/human output. Real
empty directories and completed exclusions are known zero. Counted siblings and
known failed-file bytes aggregate without making unknown tokens zero. Tests cover
real unreadable directories, deadline-before-child-enumeration, unknown-only file
parents, mixed roots, known-zero exclusions and human/JSON agreement. Schema,
statuses and exit priorities remain unchanged.

F09/F18 human rendering now escapes literal backslashes, U+2028/U+2029 and existing
control/format/surrogate classes. New tests cover ambiguous literal escapes, root
and link target rendering, splitlines and unchanged native JSON path values.

N-3/N-5 remain capability gaps. Benign installed-wheel40-file profile:9.049121 s
wall,9.009823 s CPU,93,404 KiB maximum waited-process RSS (not aggregate memory).
Three interpreter startup measurements14–22 ms; worker imports30–39 ms; startup
plus tokenizer load/count228–231 ms. Linear projection530.44 tinyfiles/120 s is
explicitly workload-specific, not a fixed cap. No proved local optimization was
identified; retain fresh private worker lifecycle. Bounded subtree selection is
an immediate workflow alternative. Persistent batching/pools need Orc adjudication.
Mandatory Linux user/PID namespaces and pidfds remain fail-closed; restricted-host
and non-Linux support stay open. README reconciles actual limits/null/strict/hosts.

Source full suite37 passed in21.415 s under115 s wall/60 s CPU/2 GiB outer bounds.
The profile uses a provisional fixed wheel; final tracked source/artifact and four
installed-runtime/floor CI evidence follow in this same authorized batch.
Checksummed source log/profile: review/task-003/evidence/amendment-3-base/.
Single native observation is returned separately; no retry. Executor regressions
are not independent acceptance. Classifier-denied independent probes remain open.
Overall TASK-003 remains0/4, native phase1 open; base substages are candidates only.
