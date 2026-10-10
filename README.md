# ttree

DOC, DOCX and text-PDF counting runs locally with bounded workers.
Installing this revision updates the command; changing a source checkout alone does not.

`ttree` prints a directory tree with estimated token counts. Counting runs locally
with `tiktoken` and the bundled, SHA-256-verified `o200k_base` vocabulary.
Counts describe extracted file contents, not full conversation context or exact
model billing. It does not depend on `tree`, an API, or a first-run download.

```bash
ttree -L 2 docs notes --sort
ttree -hL 2 docs --sort          # also show byte sizes
ttree --exact docs              # exact tokens, with dot thousands separators
```

Tokens are compact by default (`1,2 ktok`, `24,9 Mtok`). `-h`/`--human` adds compact
byte sizes (`68 kB`, `1,2 MB`). Use `-h --exact` for exact bytes and tokens
(`1.234.567 B`). Unlike v0.1.0, bytes are hidden by default.
`-L` limits displayed depth; `--sort` orders siblings by descending token total.
Directory totals include all descendants, even below the displayed depth.
A collapsed directory shows extension counts, such as `guides/ {7 × .md}`.
With multiple roots, the last line shows their combined total.

## Install

Python 3.10+ on Linux is required. Install the current main revision with `uv`:

```bash
uv tool install git+https://github.com/indes-dev/ttree.git@main
ttree --help
```

Or use `pip` inside your existing Python environment:

```bash
python -m pip install git+https://github.com/indes-dev/ttree.git@main
```

Installation fetches the Python packages. Subsequent runs need no network or API
key. There are three direct Python dependencies: `tiktoken`, `pypdf` and the small
pure-Python OLE reader `olefile`; installers
resolve their dependencies automatically. DOCX needs no additional library.
No LibreOffice, Pandoc, Poppler or OCR tool is required for DOCX or PDF.
Legacy DOC needs no native program. Its static reader reads stored Word binary
text without launching LibreOffice, evaluating fields or opening embedded objects.
The project is validated on Linux; macOS and Windows have not been validated.
Binary wheel availability depends on Python version and platform.
See [THIRD_PARTY.md](THIRD_PARTY.md) for the bundled vocabulary notice.

## Counted content

- UTF-8 text and BOM-marked UTF-16/UTF-32 files are counted locally. Hidden entries require `-a`. Symbolic
  links are shown but never followed.
- **DOCX:** extract paragraphs, headings, lists and table cell text from the ZIP's
  WordprocessingML. Count headers, footers and notes once per XML part. Paragraphs
  use line breaks, common heading styles use `#`, lists use `-`, and table cells
  use tabs. Formatting is a small text representation, not a complete rendering
  of Word. Images, deleted revisions, field instructions and embedded objects
  and moved-from revisions do not contribute text. AlternateContent chooses one
  supported Word namespace branch or its fallback. Duplicate ZIP members and
  DTD/entity declarations are rejected. XML extraction has actual 4 MiB per-part / 8 MiB aggregate expansion limits.
- **PDF:** use `pypdf` to extract the existing text layer. No OCR runs. Image-only
  files show `[no text]`. Existing text layers, including previously OCRed layers,
  are readable; layout, font encoding and extraction order can affect estimates.
  Only an empty user password is tried. Other encrypted PDFs show `[encrypted]`
  with unknown tokens. Recovery warnings make a result incomplete.
- **DOC:** read Word 97–2003 binary piece-table text, including stored auxiliary
  stories such as headers and notes. Paragraphs become newlines and table cell
  marks become tabs. Field instructions are skipped; their saved display text is
  counted. Macros, DDE, links and embedded objects are never evaluated. This is
  stored text, not a rendered Word view: hidden/revision text may contribute.
  Encrypted DOC reports `[encrypted]`; pre-Word-97, RTF/HTML renamed to DOC and
  unsupported variants remain incomplete. Convert those trusted documents to DOCX
  outside ttree when necessary.

Image, audio, video and other binary files contribute bytes but no tokens. Byte
sizes always refer to the original files. Malformed or unreadable documents show
an error label; private parser messages and extracted text are not printed.
A `≥` token count marks incomplete extraction or an unreadable descendant. If no
text could be counted, an incomplete total is labelled explicitly. Errors exclude
unreadable content from totals. They do not turn it into a claimed zero estimate. The `≥` symbol identifies
incomplete extraction; it is not a mathematical lower bound for whole-document
BPE tokenization. Unknown/non-UTF-8 content and unsupported text-bearing formats
remain incomplete. Known media/archive/font/executable suffixes and descendant
symlinks are intentional complete exclusions; explicit symlink roots are incomplete.

## Offline install

The prepared artifact target is **CPython 3.12, Linux x86_64**. It contains the
application wheel, all declared dependency wheels, target manifest, hash locks,
tracked-build metadata, instructions and SHA256SUMS. Other targets need their own
measured lock/artifact; no broad platform artifact is claimed.

Prepare from an exact tracked Git revision on a connected matching machine. Build
tools and pip are preparation tools only. For this candidate:

```bash
mkdir -p .tmp
uv venv --python 3.12 --seed .venv
uv pip install --python .venv/bin/python --require-hashes -r locks/build-linux-cp312-x86_64.txt
TMPDIR="$PWD/.tmp" .venv/bin/python scripts/build_tracked.py .tmp/build
.venv/bin/python scripts/build_offline.py .tmp/build/packages/indes_ttree-0.2.0-py3-none-any.whl .tmp/offline
```

`build_tracked.py` exports committed input and fixes SOURCE_DATE_EPOCH. Both
wheel/sdist use exact file lists and reject unexpected implicit build files.
Untracked local files are excluded. `build_offline.py` requires tracked-wheel
metadata, downloads with `--require-hashes`, records the dependency lock digest,
exact package versions and target, and adds a hash-enforced install lock.

Transfer the entire artifact. Obtain its SHA256SUMS digest through an independently
trusted channel before verification; checksum files establish byte integrity and
do not establish publisher identity. No release digest is published by this task.
On the destination, use an existing compatible Python and pip, from the artifact:

```bash
sha256sum -c SHA256SUMS
python -m pip install --no-index --find-links wheels --require-hashes -r install-lock.txt
ttree --json --strict docs
```

Python and installers are excluded. The artifact includes the static DOC reader;
it does not require or install LibreOffice.

## Development

```bash
uv venv --python 3.12
uv pip install -e .
mkdir -p .tmp
TMPDIR="$PWD/.tmp" .venv/bin/python -m unittest discover -s tests -v
```

The project is licensed under MIT; see [LICENSE](LICENSE). There is no AUR package yet.

## Bounded candidate and agent results

Linux workers use user/PID namespaces and pidfds. On Linux x86_64 hosts that
restrict user namespaces, a syscall allowlist instead enforces a single process:
no fork/clone, exec, networking, ptrace or io_uring. The same memory, CPU, output,
parent-death and supervisor wall limits apply. There is no unsandboxed fallback.
If the kernel denies both containment mechanisms, counting fails closed with
`limits_unavailable`; use a Linux environment that permits one of them. Other
Linux architectures require user/PID namespaces. macOS and Windows are not
supported by this version. No host command dependencies are required for counting.
A descriptor-relative, no-follow traversal and private file snapshots prevent
redirecting reads through symlinks. Scanning, aggregation, sorting and rendering
use iterative traversal.

Defaults: 64 MiB input; DOCX 4 MiB/part, 8 MiB aggregate expanded XML, depth 128,
100,000 elements and 4,096 ZIP members; 2,000 PDF pages; 1,000,000 extracted Unicode
characters; per-worker 15 s wall / 10 s CPU / 512 MiB address space; 12 MiB response;
120 s aggregate scan work, 100,000 entries, 16 MiB combined stored path bytes.
Snapshot storage follows the input ceiling (64 MiB by default), independently of
the 12 MiB incrementally enforced IPC response ceiling. After the snapshot is
complete, subsequent worker file output is capped at the effective response limit
(12 MiB by default) as well. Lowering the
response limit does not lower the input/snapshot limit. Each file gets a fresh
Python worker in isolated mode (`-I`), a private working directory and an
allowlisted environment; caller modules and Python environment paths are excluded.
Parser allocations remain inside the process envelope even before content limits
can be checked. Output blocking is outside the scan deadline. Each `--limit-...`
option accepts a positive integer up to its displayed default; `--help` lists the
exact names. No option disables a boundary.

`ttree --json --strict docs missing` emits exactly one newline-terminated JSON
object: schema_version 1, effective_limits, roots and total. Each root preserves
its supplied path and has tokens/bytes/complete/status plus a flat entries list,
including relative path `.`. POSIX paths also have base64 raw-byte fields. Human
output escapes literal backslashes, U+2028/U+2029, terminal controls and
surrogate/format characters; JSON preserves
native paths through ordinary JSON escaping. Missing roots are retained. Display
flags (`-h`, `--exact`, `-L`, `--sort`) do not filter scanned JSON entries.

Unknown counts are null, including unenumerated unreadable/timed-out directories.
Completely enumerated empty directories, empty/no-text files and completed token
exclusions have known zero tokens. Directory/total counts sum known contributions
for each field separately and propagate incomplete descendants. If no contribution
is known, the incomplete field remains null. Failed files can retain known bytes.
`--json` does not imply
strict: exit 0 normally; 3 for incomplete results with `--strict`; 1 for missing
roots or an unrecoverable startup/run failure; 2 for usage/configuration errors.
Per-file failures allow later files and roots to continue.

Fresh isolation and vocabulary loading have a measurable per-file cost. The
120 s scan budget is a time limit, not a fixed file count. A batch that exceeds
that budget returns all enumerated entries and marks unprocessed content incomplete
(null tokens); `--strict` returns 3. Split large workloads into smaller subtrees.
The final installed-wheel measurement and exact artifact provenance are recorded
in [the completion report](docs/reviews/TASK-006-completion.md).
