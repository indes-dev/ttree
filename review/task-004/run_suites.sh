#!/usr/bin/env bash
# TASK-004: run the pinned production suites against each installed matrix env.
# Usage: review/task-004/run_suites.sh <project-root> <log-dir>
set -u
root=${1:-/home/zak/projects/ttree}
logs=${2:-review/task-004/evidence}
mkdir -p "$logs" "$root/.tmp/task-004/suites-tmp"
for v in 310 311 312 314; do
  py="$root/.tmp/matrix-$v/bin/python"
  echo "== matrix-$v"
  TMPDIR="$root/.tmp/task-004/suites-tmp" timeout --kill-after=1 115 \
    prlimit --as=2147483648 --cpu=60 --core=0 \
    "$py" -I -m unittest discover -s tests -v >"$logs/suite-$v.log" 2>&1
  echo "exit=$?"
  tail -n 3 "$logs/suite-$v.log"
done
