"""TASK-002 tokenizer cross-check: ttree's LocalTokenizer versus upstream o200k_base.

Usage (inside `unshare -Urn`, so upstream cannot download):
    python probe_tokenizer.py CACHE_DIR
The upstream constructor in tiktoken_ext.openai_public is fed the bundled vocabulary
through TIKTOKEN_CACHE_DIR (cache key = sha1 of the upstream URL); tiktoken itself
verifies the upstream expected SHA-256, so a match also authenticates the bundle.
"""

import hashlib
import os
import random
import sys
from pathlib import Path

import ttree.tokenizer as local


def main():
    cache = Path(sys.argv[1]).resolve()
    cache.mkdir(exist_ok=True)
    bundled = Path(local.__file__).parent / "data" / "o200k_base.tiktoken"
    url = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
    (cache / hashlib.sha1(url.encode()).hexdigest()).write_bytes(bundled.read_bytes())
    os.environ["TIKTOKEN_CACHE_DIR"] = str(cache)

    import tiktoken
    from tiktoken_ext import openai_public

    spec = openai_public.o200k_base()
    print(f"bundled sha256={hashlib.sha256(bundled.read_bytes()).hexdigest()}")
    print(f"pattern identical to upstream: {spec['pat_str'] == local.O200K_PATTERN}")
    print(f"upstream special tokens: {sorted(spec['special_tokens'])}")
    upstream = tiktoken.Encoding(**spec)
    mine = local.LocalTokenizer(bundled)
    print(f"ranks identical: {upstream._mergeable_ranks == mine.encoding._mergeable_ranks}")

    samples = [
        "", " ", "\n", "\r\n\r\n", "\t\t x", "Hello, world!", "  leading and trailing  ",
        "Olá, ação, coração — não é?", "Straße 1234567 €", "日本語のテキストです。", "中文文本测试",
        "한국어 텍스트", "Привет, мир", "مرحبا بالعالم", "שלום עולם", "हिन्दी पाठ", "ภาษาไทย",
        "emoji 👩‍👩‍👧‍👦 🇧🇷 ✔️", "a" * 5000, "1" * 999, "3.14159e-10 0x1F 1_000_000",
        "I'm you'RE they'll we'd SHE'S", "<|endoftext|> <|endofprompt|> <|fim_prefix|>",
        "def f(x):\n    return x ** 2  # comment\n", "{\"key\": [1, 2, {\"n\": null}]}",
        "​‍﻿ zero-width", "é combining", "\U0001F600" * 100,
        "path/to/file.txt\\windows\\path", "    \n\n\n    \n", "ALLCAPS CamelCase snake_case",
    ]
    rng = random.Random(2002)
    alphabet = [chr(c) for c in range(0x20, 0x2500) if not 0xD800 <= c <= 0xDFFF] + ["\n", "\t", " "] * 50
    samples += ["".join(rng.choice(alphabet) for _ in range(rng.randint(1, 400))) for _ in range(2000)]
    mismatches = 0
    for text in samples:
        if upstream.encode_ordinary(text) != mine.encode(text.encode()):
            mismatches += 1
    print(f"samples={len(samples)} mismatches={mismatches}")
    special = "<|endoftext|>"
    print(f"special-like text: upstream.encode raises={_raises(lambda: upstream.encode(special))} "
          f"ttree={len(mine.encode(special.encode()))} tokens (ordinary)")
    invalid, bom = bytes([0x61, 0xFF]), bytes([0xEF, 0xBB, 0xBF]) + b"hi"
    print(f"LocalTokenizer on invalid UTF-8 {invalid!r}: raises={_raises(lambda: mine.encode(invalid))}")
    print(f"BOM-prefixed UTF-8 counts: {len(mine.encode(bom))} vs plain {len(mine.encode(b'hi'))}")


def _raises(fn):
    try:
        fn()
    except Exception as error:  # report the exception class only
        return type(error).__name__
    return "no"


if __name__ == "__main__":
    main()
