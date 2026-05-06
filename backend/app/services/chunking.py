"""Chunking utilities – splits text into overlapping token windows."""
from __future__ import annotations

import tiktoken

from app.config import get_settings

settings = get_settings()
_enc = tiktoken.get_encoding("cl100k_base")


def chunk_text(text: str) -> list[str]:
    """Split *text* into overlapping chunks of `chunk_size` tokens."""
    tokens = _enc.encode(text)
    size = settings.chunk_size
    overlap = settings.chunk_overlap
    chunks: list[str] = []

    start = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(_enc.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += size - overlap

    return [c.strip() for c in chunks if c.strip()]
