"""Offline bounded token estimates; byte sizes with -h, agent results with --json."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

from ttree.limits import CAPS, validated
from ttree.scan import Entry, encoded, record, scan_roots
from ttree.tokenizer import LocalTokenizer

TOKENIZER_URL = (
    "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
)
TOKENIZER_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"


def tokenizer_path() -> Path:
    return Path(__file__).parent / "data/o200k_base.tiktoken"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_tokenizer_file(path: Path) -> None:
    if path.is_file() and file_hash(path) == TOKENIZER_SHA256:
        return
    raise RuntimeError(
        "bundled tokenizer vocabulary is missing or failed SHA-256 verification; reinstall ttree"
    )


def load_tokenizer():
    path = tokenizer_path()
    ensure_tokenizer_file(path)
    return LocalTokenizer(path)


def grouped(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def compact(value: int, units: tuple[str, ...], exact: bool) -> str:
    if exact or value < 1000:
        return f"{grouped(value)} {units[0]}"
    amount = float(value)
    unit = 0
    while amount >= 1000 and unit < len(units) - 1:
        amount /= 1000
        unit += 1
    number = f"{amount:.1f}".replace(".", ",").removesuffix(",0")
    return f"{number} {units[unit]}"


def size_label(size: int, exact: bool) -> str:
    return compact(size, ("B", "kB", "MB", "GB", "TB"), exact)


def escape(value):
    chunks = []
    for char in value:
        code = ord(char)
        if (
            code < 32
            or 0x7F <= code <= 0x9F
            or unicodedata.category(char) in {"Cf", "Cs"}
        ):
            chunks.append("\\u%04x" % code if code <= 0xFFFF else "\\U%08x" % code)
        else:
            chunks.append(char)
    return "".join(chunks)


def measure(entry, exact, human):
    values = []
    if human and entry.bytes is not None:
        values.append(size_label(entry.bytes, exact))
    if entry.tokens is not None:
        values.append(
            ("" if entry.complete else "≥")
            + compact(entry.tokens, ("tok", "ktok", "Mtok", "Gtok"), exact)
        )
    if entry.status not in {"counted", "empty"}:
        values.append(entry.status)
    return " | ".join(values)


def extension_label(root):
    counts = Counter()
    pending = [root]
    while pending:
        entry = pending.pop()
        if entry.kind == "directory":
            pending.extend(entry.children)
        elif entry.kind == "file":
            counts[Path(entry.name).suffix.lower() or "sem extensão"] += 1
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], os.fsencode(pair[0])))
    shown = [str(count) + " × " + escape(suffix) for suffix, count in ordered[:3]]
    if len(ordered) > 3:
        shown.append("+" + str(len(ordered) - 3) + " tipos")
    return " {" + ", ".join(shown) + "}" if shown else ""


def render(root, *, exact=False, depth=None, sort=False, human=False):
    pending = [(root, "", 0, "")]
    while pending:
        entry, stem, level, branch = pending.pop()
        name = escape(entry.name) + (
            "/" if entry.kind == "directory" and not entry.name.endswith("/") else ""
        )
        if entry.target is not None:
            name += " -> " + escape(entry.target)
        if entry.kind == "directory" and depth is not None and level == depth:
            name += extension_label(entry)
        label = measure(entry, exact, human)
        yield stem + branch + (("[" + label + "] ") if label else "") + name
        if depth is not None and level >= depth:
            continue
        ordered = sorted(
            entry.children,
            key=(lambda item: (-(item.tokens or 0), os.fsencode(item.name)))
            if sort
            else (lambda item: os.fsencode(item.name)),
        )
        child_stem = stem + ("    " if branch == "└── " else "│   ") if level else ""
        for index in range(len(ordered) - 1, -1, -1):
            pending.append(
                (
                    ordered[index],
                    child_stem,
                    level + 1,
                    "└── " if index == len(ordered) - 1 else "├── ",
                )
            )


def output_json(roots, limits):
    values = []
    for path, entries in roots:
        root = entries[0]
        values.append(
            {
                **encoded(path),
                "tokens": root.tokens,
                "bytes": root.bytes,
                "complete": root.complete,
                "status": root.status,
                "entries": [record(item) for item in entries],
            }
        )
    total = {
        "tokens": sum(root[1][0].tokens or 0 for root in roots),
        "bytes": sum(root[1][0].bytes or 0 for root in roots),
        "complete": all(root[1][0].complete for root in roots),
    }
    print(
        json.dumps(
            {
                "schema_version": 1,
                "effective_limits": limits,
                "roots": values,
                "total": total,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        )
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ttree", add_help=False, description=__doc__)
    parser.add_argument("--help", action="help")
    parser.add_argument("-h", "--human", action="store_true")
    parser.add_argument("--exact", action="store_true")
    parser.add_argument("-L", "--level", type=int)
    parser.add_argument("-a", "--all", action="store_true")
    parser.add_argument("--sort", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 3 for incomplete results; missing roots still exit 1",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="one schema-version-1 document with all scanned entries",
    )
    for key, value in CAPS.items():
        parser.add_argument(
            "--limit-" + key.replace("_", "-"),
            type=int,
            default=value,
            metavar="N",
            help="positive ceiling; maximum " + str(value),
        )
    parser.add_argument("paths", nargs="*", default=["."])
    args = parser.parse_args(argv)
    if args.level is not None and args.level < 1:
        parser.error("-L must be at least 1")
    try:
        limits = validated({key: getattr(args, "limit_" + key) for key in CAPS})
    except ValueError:
        parser.error("limits must be positive integers within the documented ceilings")
    if len(args.paths) > limits["entries"]:
        parser.error("root count exceeds the entry budget")
    deadline = time.monotonic() + limits["scan_seconds"]
    try:
        ensure_tokenizer_file(tokenizer_path())
        roots = scan_roots(args.paths, limits, deadline, args.all)
    except (OSError, RuntimeError, ValueError):
        print("ttree: startup or scan failed", file=sys.stderr)
        roots = [
            (path, [Entry(".", path, "other", status="failed")]) for path in args.paths
        ]
        if args.json:
            output_json(roots, limits)
        return 1
    if args.json:
        output_json(roots, limits)
    else:
        for index, (_, entries) in enumerate(roots):
            if index:
                print()
            for line in render(
                entries[0],
                exact=args.exact,
                depth=args.level,
                sort=args.sort,
                human=args.human,
            ):
                print(line)
        if len(roots) > 1:
            combined = Entry(
                ".",
                "Total",
                "directory",
                tokens=sum(items[0].tokens or 0 for _, items in roots),
                bytes=sum(items[0].bytes or 0 for _, items in roots),
                status="counted"
                if all(items[0].complete for _, items in roots)
                else "partial",
            )
            print("\nTotal: [" + measure(combined, args.exact, args.human) + "]")
    if any(items[0].status == "missing" for _, items in roots):
        return 1
    return 3 if args.strict and any(not items[0].complete for _, items in roots) else 0


if __name__ == "__main__":
    raise SystemExit(main())
