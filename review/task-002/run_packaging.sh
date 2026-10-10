#!/usr/bin/env bash
# Packaging and offline-artifact checks following README "Offline install".
# Builds twice for reproducibility, inspects contents, builds the offline artifact
# (this step downloads public wheels from PyPI), then validates it offline.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../.." && pwd)
out=${OUT:-$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-pkg.XXXXXX")}
echo "out=$out"
cd "$repo"
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct 9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e)
echo "## dirty-checkout sdist (README 'uv build' from a checkout with untracked files)"
uv build --quiet --sdist --out-dir "$out/dirty" 2>&1 | tail -3
ls "$out"/dirty/*.tar.gz >/dev/null 2>&1 && tar -tzf "$out"/dirty/*.tar.gz | cut -d/ -f2 | sort | uniq -c
echo "## clean builds from git archive of the implementation commit"
for n in 1 2; do
  mkdir -p "$out/src$n"
  git archive 9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e | tar -x -C "$out/src$n"
  (cd "$out/src$n" && uv build --quiet --out-dir "$out/build$n") || echo "uv build $n failed"
done
echo "## build digests"
(cd "$out" && sha256sum build1/* build2/*)
echo "## wheel listing"
python3 -m zipfile -l "$out"/build1/*.whl
echo "## sdist listing"
tar -tzvf "$out"/build1/*.tar.gz
echo "## suspicious names in sdist/wheel"
{ python3 -m zipfile -l "$out"/build1/*.whl; tar -tzf "$out"/build1/*.tar.gz; } | grep -E -i '\.claude|\.review|review/task|\.env|\.pem|\.key|vault|/\.git/' || echo "none"
echo "## vocabulary inside wheel"
mkdir -p "$out/unz" && python3 -m zipfile -e "$out"/build1/*.whl "$out/unz" && sha256sum "$out"/unz/ttree/data/o200k_base.tiktoken
echo "## wheel METADATA"
cat "$out"/unz/*.dist-info/METADATA | head -40
echo "## offline artifact build (downloads public wheels)"
"$here/run_bounded.sh" 900 600 4096 uv run --no-project --python 3.12 --with pip python scripts/build_offline.py "$out"/build1/indes_ttree-0.2.0-py3-none-any.whl "$out/offline"
ls -la "$out/offline/wheels"
cat "$out/offline/manifest.json"
echo "## offline validation (unshare -Urn)"
uv venv --quiet --python 3.12 "$out/val-venv"
"$here/run_bounded.sh" 900 600 4096 unshare -Urn "$out/val-venv/bin/python" scripts/validate_offline.py "$out/offline"
echo "## pip path without uv, offline"
"$here/run_bounded.sh" 900 600 4096 unshare -Urn sh -c "'$out/val-venv/bin/python' -m ensurepip --default-pip >/dev/null 2>&1; '$out/val-venv/bin/python' -m pip install --quiet --no-index --find-links '$out/offline/wheels' indes-ttree==0.2.0 && '$out/val-venv/bin/ttree' --exact '$repo/README.md'"
