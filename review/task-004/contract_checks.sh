#!/usr/bin/env bash
# TASK-004: DOC quarantine and exit precedence on plain-text fixtures.
# Usage: review/task-004/contract_checks.sh <ttree-bin> <fixture-dir>
set -u
t=$1; d=$2
run() {
  TMPDIR="$d/../suites-tmp" timeout --kill-after=1 115 \
    prlimit --as=2147483648 --cpu=60 --core=0 "$t" "$@"
}
echo "== json quarantine dir"
run --json "$d" | python3 -I -c '
import json, sys
doc = json.load(sys.stdin)
r = doc["roots"][0]
print("root", r["status"], r["tokens"], r["bytes"], r["complete"])
for e in r["entries"][1:]:
    print(" ", e["path"], e["status"], e["tokens"], e["bytes"], e["complete"])
print("total", doc["total"])'
run "$d" >/dev/null; echo "non-strict exit=$?"
run --strict "$d" >/dev/null; echo "strict exit=$?"
run --strict "$d/c.md" >/dev/null; echo "strict complete-file exit=$?"
run --strict "$d" "$d/missing-root" >/dev/null 2>&1; echo "strict partial+missing exit=$?"
run "$d/missing-root" >/dev/null 2>&1; echo "non-strict missing exit=$?"
echo "== human multi-root total"
run "$d/c.md" "$d/missing-root" 2>/dev/null | tail -1
