"""Load the bundled o200k_base vocabulary without tiktoken's download path.

The o200k_base splitting pattern comes from OpenAI's MIT-licensed tiktoken.
See data/TIKTOKEN_LICENSE.
"""

from __future__ import annotations

import base64
from pathlib import Path

O200K_PATTERN = "|".join([
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"\p{N}{1,3}",
    r" ?[^\s\p{L}\p{N}]+[\r\n/]*",
    r"\s*[\r\n]+",
    r"\s+(?!\S)",
    r"\s+",
])


class LocalTokenizer:
    def __init__(self, path: Path):
        import tiktoken

        ranks = {}
        for line in path.read_bytes().splitlines():
            token, rank = line.split()
            ranks[base64.b64decode(token)] = int(rank)
        self.encoding = tiktoken.Encoding(
            name="o200k_base", pat_str=O200K_PATTERN,
            mergeable_ranks=ranks, special_tokens={},
        )

    def encode(self, data: bytes) -> list[int]:
        # Document strings that resemble special tokens are ordinary content.
        return self.encoding.encode_ordinary(data.decode("utf-8"))
