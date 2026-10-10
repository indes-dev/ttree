#!/usr/bin/env bash
# TASK-004: run offline install controls inside a fresh network namespace.
# Usage: review/task-004/run_offline_controls.sh <project-root> <out-json>
set -u
root=$1; out=$2
py=/home/zak/.local/share/uv/python/cpython-3.12.14-linux-x86_64-gnu/bin/python3.12
mkdir -p "$root/.tmp/task-004/suites-tmp"
TMPDIR="$root/.tmp/task-004/suites-tmp" unshare -rn timeout --kill-after=1 115 \
  prlimit --as=2147483648 --cpu=60 --core=0 \
  "$py" -I review/task-004/offline_controls.py "$root/.tmp/offline-final-2" \
  "$root/.tmp/task-004/offline-controls" "$out"
echo "exit=$?"
