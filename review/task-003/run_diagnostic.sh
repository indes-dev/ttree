#!/usr/bin/env bash
# No sudo or persistent units. Trusted supervisor stays outside reader scopes.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
work=${1:?pass a fresh private project .tmp/ directory}
mode=${2:?enforcement or doc}
exec timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0 \
  "$root/.venv/bin/python" "$root/review/task-003/diagnostic.py" "$work" "$mode"
