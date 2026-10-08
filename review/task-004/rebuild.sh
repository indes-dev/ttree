#!/usr/bin/env bash
# TASK-004: repeat the tracked build at the pinned revision and hash the outputs.
# Usage: review/task-004/rebuild.sh <project-root> <revision> <out-dir> <log>
set -u
root=$1; rev=$2; out=$3; log=$4
TMPDIR="$root/.tmp/task-004/suites-tmp" timeout --kill-after=1 115 \
  prlimit --as=2147483648 --cpu=60 --core=0 \
  "$root/.venv/bin/python" scripts/build_tracked.py --revision "$rev" "$out" >"$log" 2>&1
echo "exit=$?"
sha256sum "$out"/packages/*
