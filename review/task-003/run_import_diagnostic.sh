#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
work=${1:?pass a fresh project .tmp/ directory}
exec timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0 --fsize=12582912 \
  "$root/.venv/bin/python" "$root/review/task-003/import_diagnostic.py" "$work"
