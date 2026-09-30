# ttree

`ttree` prints a `tree`-style view with byte size and estimated token count. It uses Gigatoken with OpenAI's `o200k_base` vocabulary as one consistent local yardstick. Counts are for file contents, not full conversation context or exact Claude usage. It does not depend on the `tree` program.

```bash
ttree -L 2 docs notes --sort
```

Sizes and tokens are compact by default (`68 kB`, `1,2 MB`, `24,9 Mtok`). `-h` remains accepted for compatibility. Use `--exact` for exact values with dot thousands separators (`1.234.567 B`). `-L` limits displayed depth; `--sort` orders siblings by descending token total. Directory totals include all descendants, even below the displayed depth. A collapsed directory shows the extension counts below it, such as `guides/ {7 × .md}`.

Image, audio, video, and PDF files show disk size only and are excluded from token totals. Other files are counted if they contain UTF-8 text; binary files also show disk size only. Hidden entries are excluded unless `-a` is set. Symbolic links are shown but never followed. A `≥` token count means at least one descendant could not be read. With multiple roots, the last line shows their combined total. `--help` lists all options.

## Install

```bash
uv tool install git+https://github.com/indes-dev/ttree.git
ttree --help
```

Python 3.10+ and a supported Gigatoken platform are required. The project has been tested on Linux; macOS and Windows have not yet been validated by this project. On the first count, `ttree` downloads the tokenizer vocabulary from OpenAI and verifies its SHA-256 (`446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d`). Later counts use the local copy and do not need network access. Document contents stay local. The cache uses `XDG_DATA_HOME` when set, `LOCALAPPDATA` on Windows, and the standard per-user data directory otherwise.

For local development, run `uv tool install --editable .` from this repository. The project is licensed under MIT; see [LICENSE](LICENSE). There is no AUR package yet.
