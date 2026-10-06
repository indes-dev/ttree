# ttree

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

Python 3.10+ is required. Install directly from this public repository with `uv`:

```bash
uv tool install git+https://github.com/indes-dev/ttree.git
ttree --help
```

Or use `pip` inside your existing Python environment:

```bash
python -m pip install git+https://github.com/indes-dev/ttree.git
```

Installation fetches the Python packages. Subsequent runs need no network or API
key. There are two direct Python dependencies: `tiktoken` and `pypdf`; installers
resolve their dependencies automatically. DOCX needs no additional library.
No LibreOffice, Pandoc, Poppler or OCR tool is required for DOCX or PDF.
Legacy DOC support alone needs an optional local LibreOffice installation.
The project is validated on Linux; macOS and Windows have not been validated.
Binary wheel availability depends on Python version and platform.
See [THIRD_PARTY.md](THIRD_PARTY.md) for the bundled vocabulary notice.

## Counted content

- UTF-8 text files are counted directly. Hidden entries require `-a`. Symbolic
  links are shown but never followed.
- **DOCX:** extract paragraphs, headings, lists and table cell text from the ZIP's
  WordprocessingML. Count headers, footers and notes once per XML part. Paragraphs
  use line breaks, common heading styles use `#`, lists use `-`, and table cells
  use tabs. Formatting is a small text representation, not a complete rendering
  of Word. Images, deleted revisions, field instructions and embedded objects
  do not contribute text. XML extraction has a 32 MiB uncompressed limit.
- **PDF:** use `pypdf` to extract the existing text layer. No OCR runs. Image-only
  files show `[no text]`. Existing text layers, including previously OCRed layers,
  are readable; layout, font encoding and extraction order can affect estimates.
  Encrypted PDFs show `[encrypted PDF]` without a token estimate.
- **DOC:** use LibreOffice headlessly with a temporary private profile and copy.
  Macros and automatic external link updates are disabled. The reader has a
  60-second timeout per file. Without LibreOffice, show a reader-unavailable
  label and continue counting other files.

Image, audio, video and other binary files contribute bytes but no tokens. Byte
sizes always refer to the original files. Malformed or unreadable documents show
an error label; private parser messages and extracted text are not printed.
A `≥` token count marks incomplete extraction or an unreadable descendant. If no
text could be counted, an incomplete total is labelled explicitly. Errors exclude
unreadable content from totals. They do not turn it into a claimed zero estimate.

## Offline install

A complete offline artifact contains the `ttree` wheel (including the vocabulary),
all dependency wheels, `manifest.json`, instructions and `SHA256SUMS`.
Prepare it on a connected machine with the same Python, OS and architecture as
the destination. Build tools and pip are only needed to prepare the artifact:

```bash
uv build
uv run --no-project --with pip python scripts/build_offline.py \
  dist/indes_ttree-0.2.0-py3-none-any.whl dist/offline
```

Transfer the entire `dist/offline` directory and its independently recorded
`SHA256SUMS` checksum. On the destination, use an existing compatible Python and
`uv` or `pip`. From the artifact directory:

```bash
sha256sum -c SHA256SUMS
uv tool install --offline --no-index --no-python-downloads \
  --find-links wheels indes-ttree==0.2.0
ttree docs
```

For a destination without `uv`, use an existing pip environment:

```bash
python -m pip install --no-index --find-links wheels indes-ttree==0.2.0
```

The artifact intentionally excludes Python itself, installer executables and
optional LibreOffice. Prepare a separate wheel artifact for each target platform.

## Development

```bash
uv venv
uv pip install -e .
.venv/bin/python -m unittest discover -s tests -v
unshare -Urn .venv/bin/python scripts/validate_offline.py dist/offline
```

The project is licensed under MIT; see [LICENSE](LICENSE). There is no AUR package yet.
