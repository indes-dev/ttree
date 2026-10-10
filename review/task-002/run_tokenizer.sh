#!/usr/bin/env bash
# Tokenizer cross-check against upstream o200k_base, offline (user + network namespace).
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
py=${PYTHON:-$here/../../.review/venv-312/bin/python}
work=$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-tok.XXXXXX")
"$here/run_bounded.sh" 600 300 4096 unshare -Urn "$py" "$here/probe_tokenizer.py" "$work/cache"
rm -rf "$work"
