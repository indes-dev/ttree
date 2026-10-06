#!/usr/bin/env bash
# Lowest allowed direct dependencies (pyproject floors): does the suite pass, and do
# published pypdf advisories become reachable through ttree? Downloads public wheels.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
venv=${VENV:-$repo/.review/venv-lowest}
uv venv --quiet --python 3.12 "$venv"
uv pip install --quiet --python "$venv/bin/python" --resolution lowest-direct "$repo"
uv pip list --python "$venv/bin/python" | grep -E -i 'tiktoken|pypdf|regex|ttree'
echo "## suite with lowest-direct"
(cd "$repo" && "$venv/bin/python" -m unittest discover -s tests 2>&1 | tail -3)
echo "## PDF probes with lowest-direct pypdf"
PYTHON="$venv/bin/python" "$here/run_pdf.sh" baseline flate_bomb page_tree_amplification corrupt_xref operator_flood shared_flood_2
