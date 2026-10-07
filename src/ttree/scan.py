"""Iterative, descriptor-relative no-follow traversal and known-value aggregation."""

from __future__ import annotations

import base64
import errno
import os
import stat
import time
from dataclasses import dataclass, field
from pathlib import PurePath

from ttree.bounded import count_fd

MEDIA = {
    ".aac",
    ".avif",
    ".bmp",
    ".flac",
    ".gif",
    ".heic",
    ".ico",
    ".jpeg",
    ".jpg",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".opus",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".wav",
    ".webm",
    ".webp",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".tar",
    ".exe",
    ".dll",
    ".so",
    ".pyc",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
}
UNSUPPORTED = {".doc", ".ppt", ".pptx", ".xls", ".xlsx", ".odt", ".ods", ".odp", ".rtf"}
COMPLETE = {"counted", "empty", "no_text", "excluded"}
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


@dataclass
class Entry:
    relative_path: str
    name: str
    kind: str
    tokens: int | None = None
    bytes: int | None = None
    status: str = "counted"
    children: list = field(default_factory=list)
    target: str | None = None

    @property
    def complete(self):
        return self.status in COMPLETE


def encoded(path):
    result = {"path": path}
    if os.name == "posix":
        result["path_bytes_base64"] = base64.b64encode(os.fsencode(path)).decode(
            "ascii"
        )
    return result


def record(entry):
    value = {
        "path": entry.relative_path,
        "kind": entry.kind,
        "tokens": entry.tokens,
        "bytes": entry.bytes,
        "complete": entry.complete,
        "status": entry.status,
    }
    if os.name == "posix":
        value["path_bytes_base64"] = base64.b64encode(
            os.fsencode(entry.relative_path)
        ).decode("ascii")
    return value


def error_status(exc):
    if exc.errno == errno.ENOENT:
        return "missing"
    if exc.errno in (errno.ELOOP, errno.ENOTDIR):
        return "link_not_followed"
    return "unreadable"


def same(left, right):
    return (left.st_dev, left.st_ino, left.st_mode) == (
        right.st_dev,
        right.st_ino,
        right.st_mode,
    )


def open_root(raw):
    # Do not resolve(): every ancestor is opened relative to a retained descriptor.
    parts = PurePath(raw if raw.startswith("/") else os.getcwd() + "/" + raw).parts
    fd = os.open("/", DIR_FLAGS)
    try:
        for part in parts[1:-1]:
            new = os.open(part, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = new
        name = parts[-1] if len(parts) > 1 else "."
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            return fd, name, info, None
        try:
            opened = os.open(
                name, DIR_FLAGS if stat.S_ISDIR(info.st_mode) else FILE_FLAGS, dir_fd=fd
            )
        except OSError as exc:
            exc.known_info = info
            raise
        if not same(info, os.fstat(opened)):
            os.close(opened)
            raise OSError(errno.ESTALE, "changed")
        return fd, name, info, opened
    except BaseException:
        os.close(fd)
        raise


def classify(info):
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode):
        return "file"
    if stat.S_ISLNK(info.st_mode):
        return "link"
    return "other"


def file_count(entry, fd, limits, deadline):
    suffix = PurePath(entry.name).suffix.lower()
    if suffix in UNSUPPORTED:
        entry.status = "unsupported"
        return
    if suffix in MEDIA:
        entry.status = "excluded"
        return
    if entry.bytes > limits["input_bytes"]:
        entry.status = "too_large"
        return
    result = count_fd(
        fd, suffix[1:] if suffix in {".docx", ".pdf"} else "text", limits, deadline
    )
    entry.status = result["status"]
    entry.tokens = result["tokens"]


def scan_roots(paths, limits, deadline, include_hidden=False):
    roots = []
    used = len(paths)
    path_bytes = sum(len(os.fsencode(raw)) for raw in paths)
    for raw in paths:
        root = Entry(".", raw, "other")
        flat = [root]
        roots.append((raw, flat))
        if (
            time.monotonic() >= deadline
            or used > limits["entries"]
            or path_bytes > limits["path_bytes"]
        ):
            root.status = "timed_out" if time.monotonic() >= deadline else "too_large"
            continue
        parent_fd = root_fd = None
        try:
            parent_fd, name, info, root_fd = open_root(raw)
            root.kind = classify(info)
            if root.kind == "link":
                root.status = "link_not_followed"
                root.bytes = info.st_size
                root.target = os.readlink(name, dir_fd=parent_fd)
                continue
            if root.kind == "other":
                root.status = "unsupported"
                continue
            if root.kind == "file":
                root.bytes = info.st_size
                file_count(root, root_fd, limits, deadline)
                continue
            expected = {(): info}
            pending = [(root, ())]

            def parent_for(parts):
                fd = os.dup(root_fd)
                try:
                    for index, part in enumerate(parts):
                        new = os.open(part, DIR_FLAGS, dir_fd=fd)
                        os.close(fd)
                        fd = new
                        if not same(expected[parts[: index + 1]], os.fstat(fd)):
                            raise OSError(errno.ESTALE, "changed")
                    return fd
                except BaseException:
                    os.close(fd)
                    raise

            while pending:
                if time.monotonic() >= deadline:
                    for entry, _ in pending:
                        entry.status = "timed_out"
                    break
                entry, parts = pending.pop()
                fd = None
                try:
                    if entry.kind == "file":
                        parent = parent_for(parts[:-1])
                        try:
                            fd = os.open(parts[-1], FILE_FLAGS, dir_fd=parent)
                        finally:
                            os.close(parent)
                        current = os.fstat(fd)
                        if (
                            not same(expected[parts], current)
                            or current.st_size != entry.bytes
                        ):
                            entry.status = "changed"
                            continue
                        file_count(entry, fd, limits, deadline)
                        continue
                    fd = parent_for(parts)
                    before = os.fstat(fd)
                    with os.scandir(fd) as iterator:
                        for child in iterator:
                            if not include_hidden and child.name.startswith("."):
                                continue
                            relative = "/".join((*parts, child.name))
                            cost = len(os.fsencode(relative))
                            if (
                                used >= limits["entries"]
                                or path_bytes + cost > limits["path_bytes"]
                            ):
                                entry.status = "too_large"
                                break
                            if time.monotonic() >= deadline:
                                entry.status = "timed_out"
                                break
                            used += 1
                            path_bytes += cost
                            item = Entry(relative, child.name, "other")
                            entry.children.append(item)
                            flat.append(item)
                            try:
                                meta = child.stat(follow_symlinks=False)
                                item.kind = classify(meta)
                                if item.kind == "link":
                                    item.status = "excluded"
                                    item.bytes = meta.st_size
                                    item.target = os.readlink(child.name, dir_fd=fd)
                                elif item.kind in {"file", "directory"}:
                                    if item.kind == "file":
                                        item.bytes = meta.st_size
                                    next_parts = (*parts, child.name)
                                    expected[next_parts] = meta
                                    pending.append((item, next_parts))
                                else:
                                    item.status = "unsupported"
                            except OSError:
                                item.status = "unreadable"
                    after = os.fstat(fd)
                    if (
                        before.st_mtime_ns != after.st_mtime_ns
                        or before.st_ctime_ns != after.st_ctime_ns
                    ):
                        entry.status = "changed"
                except OSError:
                    # A replaced child/ancestor must not be mistaken for original
                    # content, even when replacement is another regular directory.
                    entry.status = "changed"
                finally:
                    if fd is not None:
                        os.close(fd)
            for entry in reversed(flat):
                if entry.kind == "directory":
                    entry.tokens = sum(item.tokens or 0 for item in entry.children)
                    entry.bytes = sum(item.bytes or 0 for item in entry.children)
                    if entry.status == "counted" and any(
                        not item.complete for item in entry.children
                    ):
                        entry.status = "partial"
        except OSError as exc:
            known = getattr(exc, "known_info", None)
            if known is not None:
                root.kind = classify(known)
                if root.kind == "file":
                    root.bytes = known.st_size
            root.status = "changed" if exc.errno == errno.ESTALE else error_status(exc)
            if root.status == "missing":
                root.kind = "missing"
            elif root.status == "link_not_followed":
                root.kind = "link"
        finally:
            if root_fd is not None:
                os.close(root_fd)
            if parent_fd is not None:
                os.close(parent_fd)
    return roots
