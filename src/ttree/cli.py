"""Display file bytes and GPT-oriented token estimates in a tree."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

TOKENIZER_URL = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
TOKENIZER_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
MAX_TOKENIZER_BYTES = 16 * 1024 * 1024

MEDIA_SUFFIXES = {
    ".aac", ".avif", ".bmp", ".flac", ".gif", ".heic", ".ico",
    ".jpeg", ".jpg", ".m4a", ".mkv", ".mov", ".mp3", ".mp4",
    ".ogg", ".opus", ".pdf", ".png", ".svg", ".tif", ".tiff",
    ".wav", ".webm", ".webp",
}


@dataclass
class Entry:
    path: Path
    name: str
    kind: str
    size: int = 0
    tokens: int = 0
    counted: int = 0
    files: int = 0
    incomplete: bool = False
    children: list[Entry] = field(default_factory=list)


def tokenizer_path() -> Path:
    if os.environ.get("XDG_DATA_HOME"):
        data_home = Path(os.environ["XDG_DATA_HOME"])
    elif os.name == "nt":
        data_home = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        data_home = Path.home() / "Library/Application Support"
    else:
        data_home = Path.home() / ".local/share"
    return data_home / "ttree/o200k_base.tiktoken"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_tokenizer_file(path: Path) -> None:
    if path.is_file() and file_hash(path) == TOKENIZER_SHA256:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix="o200k-", delete=False) as target:
            temporary = Path(target.name)
            with urlopen(TOKENIZER_URL, timeout=30) as source:
                digest = hashlib.sha256()
                total = 0
                while chunk := source.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_TOKENIZER_BYTES:
                        raise RuntimeError("tokenizer vocabulary exceeds the expected size")
                    target.write(chunk)
                    digest.update(chunk)
        if digest.hexdigest() != TOKENIZER_SHA256:
            raise RuntimeError("downloaded tokenizer vocabulary failed SHA-256 verification")
        os.replace(temporary, path)
    except (OSError, URLError) as exc:
        raise RuntimeError(f"cannot download tokenizer vocabulary: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_tokenizer():
    path = tokenizer_path()
    ensure_tokenizer_file(path)
    import gigatoken

    return gigatoken.Tokenizer.from_tiktoken(path)


def inspect(path: Path, tokenizer, include_hidden: bool) -> Entry:
    name = path.name or str(path)
    if path.is_symlink():
        return Entry(path, name, "link")
    if path.is_dir():
        entry = Entry(path, name, "dir")
        try:
            paths = [child for child in path.iterdir() if include_hidden or not child.name.startswith(".")]
        except OSError:
            entry.incomplete = True
            return entry
        for child in paths:
            item = inspect(child, tokenizer, include_hidden)
            entry.children.append(item)
            entry.size += item.size
            entry.tokens += item.tokens
            entry.counted += item.counted
            entry.files += item.files
            entry.incomplete |= item.incomplete
        return entry
    if not path.is_file():
        return Entry(path, name, "other", incomplete=True)
    if path.suffix.lower() in MEDIA_SUFFIXES:
        try:
            return Entry(path, name, "media", size=path.stat().st_size, files=1)
        except OSError:
            return Entry(path, name, "media", files=1, incomplete=True)
    try:
        raw = path.read_bytes()
    except OSError:
        return Entry(path, name, "file", files=1, incomplete=True)
    entry = Entry(path, name, "file", size=len(raw), files=1)
    if b"\0" in raw:
        return entry
    try:
        raw.decode("utf-8")
        entry.tokens = len(tokenizer.encode(raw))
        entry.counted = 1
    except (UnicodeDecodeError, ValueError):
        pass
    return entry


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


def tokens_label(item: Entry, exact: bool) -> str | None:
    if item.kind in ("link", "other", "media") or item.counted == 0 and item.files > 0:
        return None
    prefix = "≥" if item.incomplete else ""
    return prefix + compact(item.tokens, ("tok", "ktok", "Mtok", "Gtok"), exact)


def extensions(item: Entry) -> Counter[str]:
    if item.kind == "dir":
        counts: Counter[str] = Counter()
        for child in item.children:
            counts.update(extensions(child))
        return counts
    if item.kind in ("file", "media"):
        return Counter({item.path.suffix.lower() or "sem extensão": 1})
    return Counter()


def extension_label(item: Entry) -> str:
    counts = extensions(item)
    if not counts:
        return ""
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    shown = [f"{count} × {suffix}" for suffix, count in ordered[:3]]
    if len(ordered) > 3:
        shown.append(f"+{len(ordered) - 3} tipos")
    return " {" + ", ".join(shown) + "}"


def render(entry: Entry, *, exact: bool, depth: int | None, sort: bool) -> list[str]:
    def line(item: Entry, prefix: str = "", collapsed: bool = False) -> str:
        name = item.name + ("/" if item.kind == "dir" and not item.name.endswith("/") else "")
        if item.kind == "link":
            try:
                name += f" -> {os.readlink(item.path)}"
            except OSError:
                pass
        if collapsed and item.kind == "dir":
            name += extension_label(item)
        count = tokens_label(item, exact)
        measure = size_label(item.size, exact) + (f" | {count}" if count else "")
        return f"{prefix}[{measure}] {name}"

    lines = [line(entry)]

    def walk(parent: Entry, stem: str, level: int) -> None:
        if depth is not None and level >= depth:
            return
        children = sorted(parent.children, key=lambda item: (-item.tokens, item.name)) if sort else sorted(parent.children, key=lambda item: item.name)
        for index, child in enumerate(children):
            last = index == len(children) - 1
            lines.append(line(child, stem + ("└── " if last else "├── "), collapsed=depth is not None and level + 1 >= depth))
            if child.kind == "dir":
                walk(child, stem + ("    " if last else "│   "), level + 1)

    walk(entry, "", 0)
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ttree", add_help=False, description=__doc__)
    parser.add_argument("--help", action="help", help="show this help message and exit")
    parser.add_argument("-h", "--human", action="store_true", help="compact sizes (the default; kept for tree compatibility)")
    parser.add_argument("--exact", action="store_true", help="show exact bytes and tokens with dot thousands separators")
    parser.add_argument("-L", "--level", type=int, help="maximum displayed depth")
    parser.add_argument("-a", "--all", action="store_true", help="include hidden entries")
    parser.add_argument("--sort", action="store_true", help="sort siblings by token total, largest first")
    parser.add_argument("paths", nargs="*", default=["."], help="files or directories (default: current directory)")
    args = parser.parse_args(argv)
    if args.level is not None and args.level < 1:
        parser.error("-L must be at least 1")
    try:
        tokenizer = load_tokenizer()
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ttree: {exc}", file=sys.stderr)
        return 1
    failed = False
    roots: list[Entry] = []
    for index, raw_path in enumerate(args.paths):
        path = Path(raw_path)
        if not path.exists() and not path.is_symlink():
            print(f"ttree: path not found: {path}", file=sys.stderr)
            failed = True
            continue
        if index:
            print()
        entry = inspect(path, tokenizer, args.all)
        entry.name = str(path)
        roots.append(entry)
        for line in render(entry, exact=args.exact, depth=args.level, sort=args.sort):
            print(line)
    if len(roots) > 1:
        combined = Entry(Path("."), "total", "dir")
        combined.size = sum(root.size for root in roots)
        combined.tokens = sum(root.tokens for root in roots)
        combined.counted = sum(root.counted for root in roots)
        combined.files = sum(root.files for root in roots)
        combined.incomplete = any(root.incomplete for root in roots)
        count = tokens_label(combined, args.exact)
        measure = size_label(combined.size, args.exact) + (f" | {count}" if count else "")
        print(f"\nTotal: [{measure}]")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
