#!/usr/bin/env bash
# Run every DOCX probe under OS limits (60 s wall, 30 s CPU, 2 GiB address space).
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
py=${PYTHON:-$here/../../.review/venv-312/bin/python}
work=$(mktemp -d "${TMPDIR:-/tmp}/ttree-review-docx.XXXXXX")
cases="${*:-baseline utf16_entity utf16_laughs utf16_quadratic utf16_external utf8_entity lowercase_doctype
duplicate_members lying_size bomb_under_limit deep_nesting moderate_nesting many_entries
missing_document external_relationship ordering bad_note_id truncated_zip
strict_ooxml textbox_alternate_content fields_and_revisions}"
for case in $cases; do
  "$py" "$here/probe_docx.py" make "$work" "$case"
  "$here/run_bounded.sh" 60 30 2048 "$py" "$here/probe_docx.py" run "$work" "$case" 2>&1 | grep -E "^(case=|bounded:|[A-Za-z]*Error)"
done
rm -rf "$work"
