#!/usr/bin/env bash
# DOCX member that declares 100 bytes but inflates to ~2 GiB (file ~2 MiB).
# Measures peak RSS with an 8 GiB cap, then shows behaviour under a 1 GiB cap.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$here/../..
work=$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-docx2g.XXXXXX")
"$root/.review/venv-312/bin/python" "$here/probe_docx.py" make "$work" lying_size_2g
ls -l "$work"
for venv in venv-312 venv-python3; do
  for mem in 8192 1024; do
    echo "== $venv as=${mem}MiB"
    "$here/run_bounded.sh" 120 60 "$mem" "$root/.review/$venv/bin/python" "$here/probe_docx.py" run "$work" lying_size_2g 2>&1 \
      | grep -E "case=|bounded|Error"
  done
done
rm -rf "$work"
