# TASK-003 — DOCX/PDF semantics and dependency floor

Independent base stage under amendment 2. Native gate stays open; overall **0/4**.
No installed CLI/release/native policy change and no self-closure.

DOCX uses public Expat callbacks with streaming actual-byte/structure bounds.
Main document/root/body and strict/transitional Word namespaces are validated.
Formatting preserves paragraphs, common heading/list markers, table cells and
headers/footers/positive-ID notes. Deleted and moved-from content is omitted.
AlternateContent selects the first Choice whose required namespaces are supported
Word namespaces; otherwise its Fallback, exactly once. Unsupported branches never
contribute text. Namespace declarations are tracked across nested scopes. Duplicate
ZIP members, DTD/entity declarations and malformed input fail with fixed labels.
No private XML parser attributes or document-supplied exception strings.

PDF recovery WARNING+ messages are counted without formatting/forwarding. Even a
warning-only empty extraction remains partial (zero known tokens, incomplete).
Only an empty user password is attempted. Other passwords use encrypted/null;
unsupported encryption uses fixed failed/null. Parsing and tokenization stay inside
the original bounded worker, including unsafe behavior before content caps apply.

Dependency declaration now requires **pypdf>=6.19.0,<7**. Primary-source snapshot:
[GitHub advisory API](https://api.github.com/advisories?ecosystem=pip&affects=pypdf&per_page=100),
checked 2026-10-07, returned 51 records (page capacity 100). The tested floor 6.19.0
is outside every returned affected range; this is a dated snapshot, not a guarantee
about future vulnerabilities or hostile PDF safety without the process envelope.
Pinned fields/dates/URLs/ranges and raw response digest are retained in
`review/task-003/evidence/document-correctness/pypdf-advisories.json`.
The latest three ranges are <6.19.0:
[embedded files](https://github.com/py-pdf/pypdf/security/advisories/GHSA-v247-6f48-mgcj),
[appearance streams](https://github.com/py-pdf/pypdf/security/advisories/GHSA-php9-fj8v-98fj),
[alphabetical labels](https://github.com/py-pdf/pypdf/security/advisories/GHSA-w23x-9jrw-r45c).
Declared tiktoken/requests dependency closure remains unchanged.

28 full-suite tests passed in 12.427 s on Linux/Python 3.12.14/pypdf 6.19.0/tiktoken
0.14.0 before adding the actual unsupported-cipher fixture. The subsequent focused
document suite, including that fixture, is separately logged. Coverage candidates
F-04/F-07/F-08/F-10/F-11/F-14; broader resource/path/schema regressions retained.
Exact commands use project `.tmp` as TMPDIR and real subprocess workers. Synthetic
semantic assertions also inspect exact extracted text in trusted test code, then
verify the public worker's token result; extracted text never crosses public JSON.

Next: lowest-direct and locked artifact CI; target hash lock, packaging allowlists,
tracked-export/dirty-sentinel builds, integrity failures/reproducibility; installed
wheel behavior across Linux Python 3.10/3.11/3.12/3.14. Independent Claude exact SHA
review and ttree Orc per-ID closure remain outstanding.
