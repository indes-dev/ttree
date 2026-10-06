"""TASK-002 filesystem and agent-consumption probes through the installed CLI.

Usage: python probe_cli.py WORKDIR TTREE_EXECUTABLE
Every invocation runs the real console script as a subprocess and records
exit status, stdout and stderr exactly (repr), so that an agent's view is visible.
Large and deep cases are bounded by run_cli.sh. Synthetic fixtures only.
"""

import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def run(ttree: str, *args: str, cwd: Path, env=None, limit_mib: int | None = None, timeout: int = 120) -> None:
    command = [ttree, *args]
    if limit_mib:
        command = ["prlimit", f"--as={limit_mib * 1024 * 1024}", "--", *command]
    try:
        done = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout, env=env)
        out, err, status = done.stdout, done.stderr, done.returncode
    except subprocess.TimeoutExpired:
        out, err, status = b"", b"", "timeout"
    tail = err.decode(errors="replace").strip().splitlines()
    print(f"$ ttree {' '.join(args)}\n  exit={status}\n  stdout={out.decode(errors='backslashreplace')!r}\n"
          f"  stderr_last={tail[-1] if tail else ''!r} stderr_lines={len(tail)}")


def docx(path: Path, text: str) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')


def main():
    work, ttree = Path(sys.argv[1]).resolve(), sys.argv[2]
    names = work / "names"
    names.mkdir()
    (names / "plain.txt").write_text("hello world")
    os.close(os.open(bytes(names) + b"/latin1-\xff.txt", os.O_WRONLY | os.O_CREAT))
    (names / "esc-\x1b[2J\x1b[31mred.txt").write_text("x")
    (names / "newline\n[999 ktok] forged.txt").write_text("x")
    (names / "-L").write_text("option-like")
    os.symlink("target-\x1b]0;title\x07", names / "link-with-escape")
    print("## filenames")
    run(ttree, str(names), cwd=work)

    print("## option-like path")
    run(ttree, "-L", cwd=names)
    run(ttree, "--", "-L", cwd=names)

    print("## result semantics")
    sem = work / "semantics"
    sem.mkdir()
    (sem / "empty.txt").write_text("")
    (sem / "utf8.md").write_text("Olá, mundo")
    (sem / "latin1.txt").write_bytes("Olá, mundo — ação".encode("latin-1", "replace"))
    (sem / "utf16.txt").write_text("Hello UTF-16 text", encoding="utf-16")
    (sem / "sheet.xlsx").write_bytes(b"PK\x03\x04" + b"\0" * 64)
    (sem / "slides.odt").write_bytes(b"PK\x03\x04" + b"\0" * 64)
    (sem / "legacy.doc").write_bytes(b"\xd0\xcf\x11\xe0not really ole")
    (sem / "broken.pdf").write_bytes(b"%PDF-1.7 broken")
    docx(sem / "ok.docx", "Readable words")
    os.mkfifo(sem / "pipe.txt")
    secret = sem / "unreadable.txt"
    secret.write_text("cannot read")
    secret.chmod(0)
    locked = sem / "locked-dir"
    locked.mkdir()
    (locked / "inside.txt").write_text("hidden")
    locked.chmod(0)
    for args in ([str(sem)], ["--exact", str(sem)], ["-hL", "1", str(sem)], ["--sort", "-L", "1", str(work)]):
        run(ttree, *args, cwd=work)
    secret.chmod(0o600)
    locked.chmod(0o700)
    print("## DOC reader missing (PATH without LibreOffice)")
    run(ttree, str(sem / "legacy.doc"), cwd=work, env={"PATH": str(Path(ttree).parent), "HOME": str(work)})
    print("## complete files only")
    run(ttree, str(sem / "utf8.md"), str(sem / "ok.docx"), cwd=work)
    print("## missing root among several")
    run(ttree, str(sem / "utf8.md"), str(sem / "ok.docx"), str(work / "missing"), cwd=work)
    print("## symlinked root and symlink loops")
    sym = work / "sym"
    (sym / "real").mkdir(parents=True)
    (sym / "real" / "a.txt").write_text("some words here")
    os.symlink("real", sym / "link")
    os.symlink("loop2", sym / "loop1")
    os.symlink("loop1", sym / "loop2")
    run(ttree, str(sym / "link"), cwd=work)
    run(ttree, str(sym / "link") + "/", cwd=work)
    run(ttree, str(sym), cwd=work)
    print("## help and invalid depth")
    run(ttree, "--help", cwd=work)
    run(ttree, "-L", "0", ".", cwd=work)

    print("## deep tree")
    deep = work / "deep"
    deep.mkdir()
    fd = os.open(deep, os.O_RDONLY)
    for _ in range(1100):  # iterative: os.makedirs itself recurses past the default limit
        os.mkdir("d", dir_fd=fd)
        child = os.open("d", os.O_RDONLY, dir_fd=fd)
        os.close(fd)
        fd = child
    leaf = os.open("leaf.txt", os.O_WRONLY | os.O_CREAT, dir_fd=fd)
    os.write(leaf, b"leaf")
    os.close(leaf)
    os.close(fd)
    run(ttree, "-L", "1", str(deep), cwd=work)

    print("## large plain file (1 GiB sparse) under a 768 MiB address-space cap")
    big = work / "big"
    big.mkdir()
    with open(big / "huge.log", "wb") as handle:
        handle.truncate(1024 ** 3)
    run(ttree, str(big), cwd=work, limit_mib=768)

    print("## large UTF-8 text without whitespace (tokenizer worst case), 64 MiB")
    long = work / "long"
    long.mkdir()
    (long / "one-line.txt").write_bytes(b"a" * (64 * 1024 * 1024))
    run(ttree, str(long), cwd=work, timeout=600)


if __name__ == "__main__":
    main()
