#!/usr/bin/env bash
# Outer hard bounds; all descendants stay in the disposable PID namespace.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
work=${1:?pass a private project .tmp/ directory}
shift
nproc=$(( $(ps -L -U "$(id -u)" --no-headers | wc -l) + 64 ))
exec timeout --kill-after=2 115 prlimit --as=805306368 --cpu=60 --core=0 --nproc="$nproc" \
  unshare -Urnpf --mount-proc "$root/.venv/bin/python" \
  "$root/review/task-003/prototype.py" "$work" "$@"
