#!/usr/bin/env bash
# Real-process DOC timeout probes inside a user + network namespace, bounded.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
py=${PYTHON:-$here/../../.review/venv-312/bin/python}
work=$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-doct.XXXXXX")
"$here/run_bounded.sh" 300 120 8192 unshare -Urn "$py" "$here/probe_doc_timeout.py" "$work"
rm -rf "$work"
