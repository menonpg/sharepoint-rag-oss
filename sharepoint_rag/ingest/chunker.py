"""Token-aware overlapping text chunker.

Uses a lightweight word-based approximation (~0.75 words per token) so no
tokenizer dependency is required. Good enough for retrieval chunking.
"""

from __future__ import annotations

from dataclasses import dataclass

_WORDS_PER_TOKEN = 0.75


@dataclass
class Chunk:
    index: int
    text: str


def _tokens_to_words(tokens: int) -> int:
    return max(1, int(tokens / _WORDS_PER_TOKEN))


def chunk_text(
    text: str,
    chunk_size_tokens: int = 800,
    overlap_tokens: int = 120,
) -> list[Chunk]:
    """Split ``text`` into overlapping chunks sized roughly by token budget."""
    words = text.split()
    if not words:
        return []

    size = _tokens_to_words(chunk_size_tokens)
    overlap = _tokens_to_words(overlap_tokens)
    step = max(1, size - overlap)

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    while start < len(words):
        window = words[start : start + size]
        chunk_str = " ".join(window).strip()
        if chunk_str:
            chunks.append(Chunk(index=idx, text=chunk_str))
            idx += 1
        start += step

    return chunks
