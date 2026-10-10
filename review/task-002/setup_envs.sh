#!/usr/bin/env bash
# TASK-002 review: create isolated review environments and run the existing suite.
# Environments live under .review/ (untracked). Nothing is installed on the host.
set -euo pipefail
cd "$(dirname "$0")/../.."
for spec in 3.12 /usr/bin/python3; do
  name=venv-$(basename "$spec" | tr -d .)
  uv venv -q --python "$spec" ".review/$name"
  uv pip install -q --python ".review/$name/bin/python" -e .
  echo "== $name: $(".review/$name/bin/python" -V)"
  uv pip list --python ".review/$name/bin/python" 2>/dev/null
  (cd tests && "../.review/$name/bin/python" -m unittest discover -s . 2>&1 | tail -4)
done
