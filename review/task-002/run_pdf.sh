#!/usr/bin/env bash
# Run every PDF probe under OS limits (120 s wall, 100 s CPU, 4 GiB address space).
# Usage: run_pdf.sh [CASE...]
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
py=${PYTHON:-$here/../../.review/venv-312/bin/python}
work=$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-pdf.XXXXXX")
cases="${*:-baseline image_and_text encrypted_user encrypted_empty_user corrupt_xref damaged_page truncated
type3_font identity_cid_font launch_and_uri flate_bomb operator_flood many_pages page_tree_amplification}"
for case in $cases; do
  "$py" "$here/probe_pdf.py" make "$work" "$case"
  "$here/run_bounded.sh" 120 100 4096 "$py" "$here/probe_pdf.py" run "$work" "$case" 2>&1 \
    | grep -E "^(case=|bounded:|[A-Za-z]*Error)"
done
rm -rf "$work"
