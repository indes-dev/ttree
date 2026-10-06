#!/usr/bin/env bash
# Filesystem and agent-consumption probes through the installed console script.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
venv=${VENV:-$here/../../.review/venv-312}
work=$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-cli.XXXXXX")
"$here/run_bounded.sh" 1200 900 8192 "$venv/bin/python" "$here/probe_cli.py" "$work" "$venv/bin/ttree"
chmod -R u+rwx "$work"
rm -rf "$work"
