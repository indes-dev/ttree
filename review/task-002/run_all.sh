#!/usr/bin/env bash
# Run the whole TASK-002 matrix sequentially; one log per runner in LOGDIR.
# The packaging and lowest-direct runners download public wheels; the others are offline.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
logs=${LOGDIR:?set LOGDIR}
mkdir -p "$logs"
for runner in run_docx run_docx_2g run_pdf run_doc run_doc_timeout run_cli run_tokenizer; do
  echo "== $runner"
  "$here/$runner.sh" > "$logs/$runner.log" 2>&1
  echo "exit=$?"
done
PYTHON="$here/../../.review/venv-python3/bin/python" "$here/run_tokenizer.sh" > "$logs/run_tokenizer_314.log" 2>&1
PYTHON="$here/../../.review/venv-312/bin/python" "$here/run_pdf.sh" shared_flood_2 shared_flood_4 shared_flood_1000 > "$logs/run_pdf_shared.log" 2>&1
echo "all done"
