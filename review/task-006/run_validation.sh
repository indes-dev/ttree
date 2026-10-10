#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
cd "$root"
# The paired listener helper raises loopback only inside this disposable namespace.
exec unshare -Urnpf --mount-proc timeout --kill-after=1 90 \
  "$root/.venv/bin/python" "$root/review/task-006/validate_completion.py"
