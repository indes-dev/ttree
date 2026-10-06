#!/usr/bin/env bash
# Run the LibreOffice DOC probes inside a user + network namespace, bounded.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
py=${PYTHON:-$here/../../.review/venv-312/bin/python}
work=$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-doc.XXXXXX")
"$here/run_bounded.sh" 900 600 8192 unshare -Urn "$py" "$here/probe_doc.py" "$work"
echo "host-side leftovers in work dir:"; ls -A "$work" "$work/fixtures"
rm -rf "$work"
