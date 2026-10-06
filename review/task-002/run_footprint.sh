#!/usr/bin/env bash
# Dependency footprint: v0.1.0 (base) versus the 0.2.0 candidate under identical
# conditions (CPython 3.12, fresh venv, no pip seeded), plus runtime imports.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=${OUT:?set OUT}
for rev in 0f1d6bbd9dbb02ebc91dd0180ec4f81c09bbb361 9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e; do
  mkdir -p "$out/src-$rev"
  git -C "$repo" archive "$rev" | tar -x -C "$out/src-$rev"
  uv venv --quiet --python 3.12 "$out/venv-$rev"
  uv pip install --quiet --python "$out/venv-$rev/bin/python" "$out/src-$rev"
  echo "## $rev"
  uv pip list --python "$out/venv-$rev/bin/python" 2>/dev/null | tail -n +3
  du -s --block-size=1K "$out/venv-$rev/lib/python3.12/site-packages" | awk '{printf "site-packages: %.1f MiB\n", $1/1024}'
done
echo "## modules imported by a candidate run (network-capable modules?)"
cand="$out/venv-9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e/bin/python"
mkdir -p "$out/fx" && printf 'hello' > "$out/fx/a.txt"
"$cand" -c "import sys, runpy; sys.argv=['ttree', '$out/fx']; import ttree.cli as c; c.main(); print(sorted(m for m in sys.modules if m.split('.')[0] in {'requests','urllib3','http','socket','ssl','certifi','idna','charset_normalizer'}))"
