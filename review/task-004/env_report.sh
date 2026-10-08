#!/usr/bin/env bash
# TASK-004 preflight: record reviewer environment, runtimes and artifact identity.
# Read-only. Usage: review/task-004/env_report.sh <project-root>
set -u
root=${1:-/home/zak/projects/ttree}
tmp="$root/.tmp"
echo "kernel: $(uname -r)"
echo "max_user_namespaces: $(cat /proc/sys/user/max_user_namespaces)"
echo "nproc: $(nproc)"
for tool in prlimit timeout unshare bwrap jq uv gh git; do
  printf '%s: ' "$tool"; command -v "$tool" || echo unavailable
done
for v in 310 311 312 314; do
  env="$tmp/matrix-$v"
  printf 'matrix-%s: ' "$v"
  "$env/bin/python" -c 'import sys, ttree, tiktoken, pypdf; print(sys.version.split()[0], ttree.__file__, "tiktoken", tiktoken.__version__, "pypdf", pypdf.__version__)'
done
printf 'project .venv: '
"$root/.venv/bin/python" -c 'import sys, ttree, tiktoken, pypdf; print(sys.version.split()[0], ttree.__file__, "tiktoken", tiktoken.__version__, "pypdf", pypdf.__version__)'
cmp "$tmp/offline-final-2/wheels/indes_ttree-0.2.0-py3-none-any.whl" \
    "$tmp/tracked-build-final-2/packages/indes_ttree-0.2.0-py3-none-any.whl" \
  && echo "offline wheel == tracked wheel"
sha256sum "$tmp/tracked-build-final-2/packages/"* "$tmp/offline-final-2/SHA256SUMS"
