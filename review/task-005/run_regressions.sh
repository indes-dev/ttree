#!/usr/bin/env bash
# TASK-005: run only the five new installed-wheel regressions in each existing
# non-editable matrix env, from a private cwd, under the declared outer limits.
set -u
ROOT=/home/zak/projects/ttree
TESTS=/home/zak/projects/ttree-task004/tests
OUT=/home/zak/projects/ttree-task004/review/task-005/evidence
SCRATCH="$ROOT/.tmp/task-005/regressions"
mkdir -p "$SCRATCH" "$OUT"
for v in 310 311 312 314; do
  py="$ROOT/.tmp/matrix-$v/bin/python"
  work="$SCRATCH/$v"
  rm -rf "$work"
  mkdir -p "$work/cwd" "$work/tmp"
  log="$OUT/regressions-$v.log"
  {
    echo "env: matrix-$v"
    echo "python: $py"
    "$py" -I -c "import sys, ttree; print(sys.version.split()[0]); print(ttree.__file__)"
    echo "cwd: private $work/cwd"
    echo "limits: timeout --kill-after=1 115 prlimit --as=2147483648 --cpu=60 --core=0"
  } > "$log" 2>&1
  (
    cd "$work/cwd" || exit 2
    TMPDIR="$work/tmp" timeout --kill-after=1 115 \
      prlimit --as=2147483648 --cpu=60 --core=0 \
      "$py" -I -m unittest discover -s "$TESTS" -t "$TESTS" -v \
        -k test_isolated_worker_ignores_caller_modules \
        -k test_benign_padded_snapshot_sizes_and_independent_response_limit \
        -k test_unknown_empty_and_mixed_aggregates \
        -k test_unenumerated_timed_out_directory_and_unknown_only_parent \
        -k test_human_literal_escape_line_separators_roots_and_links
  ) >> "$log" 2>&1
  rc=$?
  echo "exit: $rc" >> "$log"
  echo "matrix-$v exit $rc"
done
