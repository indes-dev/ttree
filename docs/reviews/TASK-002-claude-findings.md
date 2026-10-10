# TASK-002 — Claude cross-review findings (phase 3)

Reviewer: independent Claude Code session (Claude Opus 5.5), posting under the
`indes-dev` GitHub identity. This is a Claude review, not a human approval.
Implementation reviewed: `9d420db2bf8b5b7a057eba0ab08ea95481ef3c9e`.
Evidence commits: `b73fd1c` (preflight and threat model) and
`822eecf0f4dc3e01f42860028288cf87f66ef538` (scripts and
`TASK-002-claude-validation.md`). Date: 2026-10-06 (UTC).
Production code was not changed. The remedies below are proposals for the Orc.

## Verdict

**Not release-ready as reviewed.** Three High findings meet the brief's blocking
criteria. Two are readily triggered, unbounded operations against untrusted files
(F-01 PDF CPU, F-03 DOCX memory). The third is unwanted external access (F-02 DOC
reader network requests). The remaining findings are Medium or Low. Most of them
concern how an agent can tell an incomplete estimate from a complete one.

Confirmed strengths:
- Tokenizer parity with upstream `o200k_base`.
- A reproducible, verified offline artifact.
- An 85.5 → 14.1 MiB footprint reduction.
- No parser text in outputs.
- No OCR.
- DOCX external relationships and OLE parts are ignored.
- The private LibreOffice copy and profile, with no lock files and no survivors after a timeout.
- A clean public history.

Severity follows the brief. **Fact** means reproduced by a committed script at
`822eecf`. **Code** means established from source. **Hypothesis** means not reproduced.

| ID | Severity | Title |
|---|---|---|
| F-01 | High | PDF extraction has no time, page or work bound |
| F-02 | High | A `.doc` holding HTML makes LibreOffice fetch remote resources |
| F-03 | High | DOCX 32 MiB budget trusts declared ZIP sizes |
| F-04 | Medium | `pypdf>=6.1` floor admits 48 published advisories; reproduced regression |
| F-05 | Medium | Exit status 0 for incomplete, failed or unsupported results |
| F-06 | Medium | Non-UTF-8 text files are silently excluded from totals |
| F-07 | Medium | PDF pages lost during recovery are not marked partial |
| F-08 | Medium | Deep trees and large plain files crash the whole run |
| F-09 | Medium | Control characters and newlines in names are printed raw |
| F-10 | Low | DOCX DTD guard is bypassed by UTF-16 parts |
| F-11 | Low | DOCX text double-counted (text boxes, moves, duplicate members) |
| F-12 | Low | Symlinked root yields no count and no marker |
| F-13 | Low | Multi-root `Total` omits a missing root without `≥` |
| F-14 | Low | PDF with an empty user password is reported as encrypted |
| F-15 | Low | DOC timeout cleanup limits (TMPDIR leftovers, escaped descendants, Windows) |
| F-16 | Low | sdist includes untracked files from the build checkout |
| F-17 | Low | Offline artifact resolution is unlocked |
| F-18 | Low | README claims exceed observed behaviour |

## Findings

### F-01 — High — PDF extraction has no time, page or work bound

- **Location:** `src/ttree/documents.py:95-118` (`extract_pdf`: `for page in reader.pages` → `page.extract_text()`). There is no caller-side bound in `src/ttree/cli.py:87-100`.
- **Trigger:** a small PDF whose pages share one content stream with many text operators (`shared_flood_N` in `review/task-002/probe_pdf.py`).
- **Impact (Fact):** about 7.1 s of CPU per page, linear in the page count. N=4: 28.9 s. A 176,764-byte file with N=1000 was killed by a 100 s CPU limit (projected about 2 h). One hostile PDF in a tree stalls `ttree` (and an agent waiting on it) indefinitely, with no label.
- **Repro:** `review/task-002/run_pdf.sh shared_flood_2 shared_flood_4 shared_flood_1000`.
- **Expected:** bounded work per file. On exceeding a bound, show a label (for example `[PDF reader timed out]`) and mark the entry incomplete.
- **Remedy:** run PDF extraction in a child process with a wall timeout (the DOC path already has the pattern), plus a CPU and address-space rlimit on POSIX. Also cap the pages and extracted characters per file, and mark the entry partial when a cap is hit. Optionally add a global deadline (see F-15, aggregate DOC cost).

### F-02 — High — A `.doc` holding HTML makes LibreOffice fetch remote resources

- **Location:** `src/ttree/documents.py:122-160` (`extract_doc`: no format check; `--convert-to txt` with no input filter).
- **Trigger:** an HTML file named `*.doc` that references a stylesheet and an image. LibreOffice detects the content type and imports it as HTML. The Writer link-update settings in the private profile do not cover that import.
- **Impact (Fact):** inside a network namespace, a loopback listener recorded 3 requests (`/html-css` ×2, `/html-img.gif`) through ttree's hardened profile. The end-to-end CLI run gave the same result with exit 0 and a normal-looking count. On a connected host this leaks the user's IP address and the fact that the file was scanned (a tracking pixel), and can reach internal URLs. RTF and FODT link vectors were not live in headless conversion, including in the permissive control.
- **Repro:** `review/task-002/run_doc.sh` (cases `html_as_doc` and the `cli` line).
- **Expected:** counting a local document makes no network access.
- **Remedy:**
  1. Before invoking the reader, require the OLE compound-file signature `D0 CF 11 E0 A1 B1 1A E1`. Otherwise label the file, for example `[not a Word 97-2003 document]`.
  2. Pass an explicit import filter (`--infilter="MS Word 97"`), so content sniffing cannot switch importers.
  3. Add a regression test that runs real LibreOffice in `unshare -rn` with a loopback listener, not a mock.
  4. Optionally, on Linux, run the reader in a network namespace when one is available.

### F-03 — High — DOCX 32 MiB budget trusts declared ZIP sizes

- **Location:** `src/ttree/documents.py:69-73` (`total += archive.getinfo(name).file_size` followed by an unbounded `archive.read(name)`).
- **Trigger:** a member whose local and central headers declare a tiny `file_size` while its deflate stream inflates to gigabytes (`lying_size_2g`).
- **Impact (Fact):** a 2,071,217-byte DOCX reached a peak RSS of 2068 MiB on 3.12 and 4085 MiB on 3.14. Deflate allows about 1000:1, so memory grows with the compressed size and the documented limit does not hold. Under a 1 GiB cap the run degrades to the `cannot extract DOCX text` label. Without a cap a 10–20 MB file can exhaust a typical workstation's RAM (Hypothesis by extrapolation; not run). An honest member just under the budget (`bomb_under_limit`, 94,860 B) costs 694 MiB and 3.1 s (Fact).
- **Repro:** `review/task-002/run_docx_2g.sh`; `review/task-002/run_docx.sh lying_size bomb_under_limit`.
- **Expected:** the 32 MiB budget limits bytes actually decompressed.
- **Remedy:** `with archive.open(name) as member: raw = member.read(remaining + 1)`, and label the file if `len(raw) > remaining`. Optionally reject a compression ratio above a threshold. Consider a lower per-part budget, since 32 MiB of XML already costs about 700 MiB of RSS in ElementTree.

### F-04 — Medium — `pypdf>=6.1` floor admits 48 published advisories; reproduced regression

- **Location:** `pyproject.toml:12` (`"pypdf>=6.1,<7"`).
- **Trigger:** installing into an environment that already has pypdf 6.1–6.18 (pip keeps an installed version that satisfies the range), or any resolver that picks the floor.
- **Impact (Fact):** the GitHub Advisory Database lists 48 pypdf advisories affecting versions in the range. Ten are HIGH, and eight of those were published 2026-10-01 with fixes only in 6.17.0–6.19.0. With pypdf 6.1.0, `page_tree_amplification` (1,867 B) ran until the 100 s CPU kill. With 6.19.0 it is rejected in 0.5 s. The suite still passes on the floor, so tests do not catch this.
- **Repro:** `review/task-002/run_lowest.sh`; `python review/task-002/probe_supply.py`.
- **Expected:** the declared floor excludes versions with known parser DoS advisories.
- **Remedy:** `pypdf>=6.19.0,<7` (raise it as new advisories land), and add a CI job with `--resolution lowest-direct`. F-01 is still required, because 6.19.0 itself does not bound F-01's case.

### F-05 — Medium — Exit status 0 for incomplete, failed or unsupported results

- **Location:** `src/ttree/cli.py:214-255` (`return 1 if failed else 0`; `failed` is set only for missing paths).
- **Trigger:** any tree containing broken/encrypted/timed-out documents, unreadable entries, a missing DOC reader or unsupported files.
- **Impact (Fact):** exit 0 in every such run (`-hL 1`, `--exact`, `--sort`, a reader-unavailable `.doc`). An agent that checks only the status, or skims for a number, can report a lower bound or an empty count as complete. Distinguishing the cases requires parsing free-text labels and a `≥` glyph.
- **Repro:** `review/task-002/run_cli.sh` (sections "result semantics" and "DOC reader missing").
- **Expected:** a machine-checkable signal of completeness.
- **Remedy (design suggestion):** see "Smallest machine-readable contract" below.

### F-06 — Medium — Non-UTF-8 text files are silently excluded from totals

- **Location:** `src/ttree/cli.py:113-118` (`except (UnicodeDecodeError, ValueError): pass`; the entry is neither counted nor `incomplete`).
- **Trigger:** a Latin-1, Windows-1252 or UTF-16 text file (common for older notes, CSV exports and Windows logs).
- **Impact (Fact):** the file is shown with no count and no marker, like an unsupported binary. The parent total gets no `≥`, so a directory of such files reports a complete-looking undercount. This contradicts the README: "A `≥` token count marks incomplete extraction or an unreadable descendant".
- **Repro:** `review/task-002/run_cli.sh` (`latin1.txt`, `utf16.txt`).
- **Expected:** either count the file (UTF-16 with a BOM is unambiguous) or label it, for example `[not UTF-8 text]`, and mark the parent incomplete.
- **Remedy:** decode BOM-marked UTF-16/32. Otherwise set `incomplete=True` with an explicit label. Add a test.

### F-07 — Medium — PDF pages lost during recovery are not marked partial

- **Location:** `src/ttree/documents.py:100-118` (pypdf runs in non-strict mode, and the `pypdf` logger is raised above CRITICAL).
- **Trigger:** a page whose content stream cannot be decoded (`damaged_page`).
- **Impact (Fact):** the result is `Good page` with `issue=None`. Page 2 is dropped silently. pypdf only logs a warning, and ttree suppresses it. The count looks complete.
- **Repro:** `review/task-002/run_pdf.sh damaged_page`.
- **Expected:** the label `cannot extract some PDF pages` and a `≥`.
- **Remedy:** attach a handler to the `pypdf` logger that counts WARNING+ records without formatting or printing them, and set the partial label when the count is non-zero. This keeps the privacy goal of not printing parser messages.

### F-08 — Medium — Deep trees and large plain files crash the whole run

- **Location:** `src/ttree/cli.py:65-83` (recursive `inspect`) and `src/ttree/cli.py:107` (`path.read_bytes()` with no size bound). The same code is in released v0.1.0.
- **Trigger:** a directory nested about 1,000 levels deep; a plain file larger than the available memory (for example a multi-GB log).
- **Impact (Fact):** a `RecursionError` traceback (33 stderr lines) with **no stdout at all**, exit 1. With a 1 GiB file under a 768 MiB cap: a `MemoryError` traceback with no output. One bad subtree loses the counts for every other root and sibling.
- **Repro:** `review/task-002/run_cli.sh` (sections "deep tree" and "large plain file").
- **Expected:** a per-entry incomplete label and output for everything else.
- **Remedy:** traverse with an explicit stack, or catch `RecursionError` per subtree and mark it incomplete. Read text in chunks up to a configurable cap, then label the file (for example `[text exceeds limit]`) and mark it incomplete. Catch `MemoryError` per entry.

### F-09 — Medium — Control characters and newlines in names are printed raw

- **Location:** `src/ttree/cli.py:187-190` (entry names and `os.readlink` targets) and `src/ttree/cli.py:236,242` (root paths on stderr and stdout). The same code is in released v0.1.0.
- **Trigger:** a file or symlink name containing ESC sequences or a newline.
- **Impact (Fact):** terminal control sequences reach the user's terminal unescaped. A newline in a name forges an extra, well-formed tree line with an arbitrary token count, which an agent can mistake for real output. A non-UTF-8 name does not crash.
- **Repro:** `review/task-002/run_cli.sh` (section "filenames").
- **Expected:** non-printable characters escaped, as in `ls -b` or `tree -q`.
- **Remedy:** render names through an escaper that maps C0, C1 and DEL (and unpaired surrogates) to `\xNN`/`?`. Apply it to names, link targets and root paths. Add a test with ESC and newline.
- **Disclosure note:** this class exists in the released v0.1.0. It is described here only at class level. The Orc should decide on routing for the released version.

### F-10 — Low — DOCX DTD guard is bypassed by UTF-16 parts

- **Location:** `src/ttree/documents.py:74` (ASCII byte search for `<!DOCTYPE`/`<!ENTITY`).
- **Trigger:** a `document.xml` encoded in UTF-16 with an internal entity.
- **Impact (Fact):** the guard is bypassed and the internal entity is expanded and counted. Expat 2.8.3 rejected billion-laughs, quadratic-blowup and external-entity variants. Hypothesis: on a Python linked to an old expat (< 2.4.1), amplification protection may be missing.
- **Repro:** `review/task-002/run_docx.sh utf16_entity utf16_laughs utf16_quadratic utf16_external`.
- **Expected:** every DTD rejected regardless of encoding.
- **Remedy:** use an `ET.XMLParser` whose underlying expat parser has a `StartDoctypeDeclHandler` (and an `EntityDeclHandler`) that raises, and keep the byte check as a fast path.

### F-11 — Low — DOCX text double-counted

- **Location:** `src/ttree/documents.py:30-56` (`_word_text` walks `mc:Choice` and `mc:Fallback`, and both `w:moveFrom` and `w:moveTo`) and `:64-67` (part names taken from `namelist()`, which repeats duplicate members).
- **Trigger:** Word text boxes and shapes with text (stored twice by design), tracked moves, and duplicate ZIP members.
- **Impact (Fact):** `BoxText` ×2, `MovedText` ×2, `Second header` ×2. The count is overestimated by the amount of that content. Text boxes are common in real Word documents.
- **Repro:** `review/task-002/run_docx.sh textbox_alternate_content fields_and_revisions duplicate_members`.
- **Expected:** each visible text counted once.
- **Remedy:** skip `mc:Fallback` when a `mc:Choice` is present, skip `w:moveFrom`, deduplicate part names, and add tests. Optional: order header/footer parts numerically (they are currently lexical; this has no effect on counts).

### F-12 — Low — Symlinked root yields no count and no marker

- **Location:** `src/ttree/cli.py:67-68` (returns a `link` entry before the directory check, also for roots) and `:235`.
- **Trigger:** `ttree link` or `ttree link/`, where `link` points to a directory. This is common for data directories that are symlinked into home.
- **Impact (Fact):** the output is only `link -> real`, exit 0, with no token count and no incompleteness signal.
- **Repro:** `review/task-002/run_cli.sh` (section "symlinked root").
- **Expected:** follow an explicitly given root (as `tree` and `du -H` do), or mark it as not followed and incomplete.
- **Remedy:** resolve symlinks for command-line roots only, and keep the no-follow rule for descendants.

### F-13 — Low — Multi-root `Total` omits a missing root without `≥`

- **Location:** `src/ttree/cli.py:246-254`.
- **Trigger:** `ttree a b missing`.
- **Impact (Fact):** exit 1 and a stderr line, but stdout ends with `Total: [5 tok]` and no `≥`.
- **Repro:** `review/task-002/run_cli.sh` (section "missing root among several").
- **Remedy:** set `combined.incomplete = True` when `failed`.

### F-14 — Low — PDF with an empty user password is reported as encrypted

- **Location:** `src/ttree/documents.py:106`.
- **Trigger:** a PDF encrypted with an empty user password, typical of permission-restricted PDFs.
- **Impact (Fact):** `[encrypted PDF]` and no estimate, although pypdf can open the file without a password.
- **Remedy (design suggestion):** try `reader.decrypt("")`, and continue if it succeeds.

### F-15 — Low — DOC timeout cleanup limits

- **Location:** `src/ttree/documents.py:164-182`.
- **Impact (Fact):**
  - After a real timeout, LibreOffice leaves an `lu*.tmp` directory tree (directories only) in the caller's `$TMPDIR`.
  - A descendant that calls `setsid` survives `killpg`. Real LibreOffice did not do this.
  - Each file may take up to 60 s, with no aggregate bound (Code).
  - On Windows only the direct child is killed (Code, Unverified at runtime).
- **Repro:** `review/task-002/run_doc_timeout.sh`.
- **Remedy:**
  - Pass `env={..., "TMPDIR": work, "TMP": work, "TEMP": work}` to the reader.
  - Document the descendant limit.
  - Use a job object or `taskkill /T` on Windows.
  - Consider an optional global deadline shared with F-01.

### F-16 — Low — sdist includes untracked files from the build checkout

- **Location:** `pyproject.toml` (no `[tool.hatch.build.targets.sdist]` include list).
- **Impact (Fact):** README's `uv build` in a checkout with untracked, non-`.gitignore`d files placed them in the sdist (here the reviewer's `.review/` venvs and `review/`). hatchling honours `.gitignore` only, not `.git/info/exclude`. A maintainer could publish local notes or data by accident.
- **Repro:** `OUT=… review/task-002/run_packaging.sh` (section "dirty-checkout sdist").
- **Remedy:** add an explicit sdist include list (`src`, `tests`, `scripts`, `README.md`, `LICENSE`, `THIRD_PARTY.md`, `pyproject.toml`), and build releases from a clean clone or from CI.

### F-17 — Low — Offline artifact resolution is unlocked

- **Location:** `scripts/build_offline.py:29-32` (`pip download` without constraints or hashes).
- **Impact (Code):** two builds on different days can select different dependency versions. The artifact's `SHA256SUMS` proves transfer integrity only, as the README states. The five network-only dependencies of tiktoken (requests, urllib3, idna, charset-normalizer, certifi; about 3.4 MiB) ship unused. This is Fact: they are never imported in a run.
- **Remedy:**
  - Commit a hashed lock or constraints file (for example `uv pip compile --generate-hashes`) and download with `--require-hashes`.
  - Record the lock digest in `manifest.json`.
  - Publish the `SHA256SUMS` digest through a separate channel (for example a signed tag or the release notes).

### F-18 — Low — README claims exceed observed behaviour

- "XML extraction has a 32 MiB uncompressed limit": not enforced for lying sizes (F-03).
- "Macros and automatic external link updates are disabled": the HTML-as-`.doc` import still fetches resources (F-02). Macro execution is Unverified (see the hypotheses below).
- "A `≥` token count marks incomplete extraction or an unreadable descendant": not true for non-UTF-8 text (F-06) or recovered PDF pages (F-07).
- **Remedy:** fix the behaviour, or narrow the wording when each related finding is resolved.

## Hypotheses (not reproduced)

- **H-A, symlink replacement race:** `cli.py:67-107` checks `is_symlink()` before `is_dir()`/`read_bytes()`. Someone who can write inside the scanned tree could swap a checked entry for a symlink and make ttree read a file outside the tree. Exposure is limited to its byte size and token count, not its content. Validation path: a racing `os.replace` loop on a disposable tree. Remedy if confirmed: `os.open(..., O_NOFOLLOW)` plus `fstat`, and `scandir` with `follow_symlinks=False`.
- **H-B, macro execution:** neither the hardened profile nor the permissive control executed the `dom:load` Basic macro, so the effect of the hardening on macros is unproven. Validation path: a fixture that the permissive control does execute.
- **H-C, DDE/OLE live update in a Word-authored `.doc`:** not tested. It needs a legitimate Word-authored fixture.
- **H-D, platforms:** the CPython 3.10/3.11 runtime, macOS and Windows were not run. Wheel availability for these platforms is confirmed from PyPI metadata.

## Smallest machine-readable contract (design suggestion for F-05)

Keep the default human output unchanged, and add two opt-in features:

1. `--strict`: exit status `3` when any counted root contains an entry in a non-complete state. `1` stays "missing root" and `2` stays "usage". This makes completeness checkable without parsing.
2. `--json`: one JSON object per root, with `path`, `tokens`, `bytes` and `complete` (bool), and `entries` as a flat list. Each entry has `path` (bytes-safe, escaped), `kind`, `tokens` (or null) and `status`. The status enum is `counted | empty | no_text | unsupported | not_utf8 | reader_unavailable | encrypted | partial | failed | timed_out | link_not_followed | unreadable | too_large`.

No free-text parser messages appear in either mode. Use the status enum as the stable API, and treat the labels as presentation only.

## Not findings (checked and confirmed)

- Tokenizer: pattern and ranks are identical to upstream, with 0 mismatches in 2,031 samples. Special-token-looking text is counted as ordinary text, which is intentional.
- Offline artifact: reproducible clean builds. `validate_offline.py` passes with the network blocked, by uv and by pip.
- History and package contents: no private material.
- Outputs: no document text on stderr. Fixed labels.
- DOCX external relationships, fields, OLE parts and images: ignored, with no network access.
- PDF actions (Launch, URI, JS): not executed. Flate bombs and page-tree loops are stopped by pypdf 6.19.0.
- DOC: a private copy (no lock files), a private 0700 work dir, and no surviving processes after a timeout with real LibreOffice.
