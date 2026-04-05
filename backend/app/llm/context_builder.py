"""Context builder — trims chunk list to fit within a token budget."""

from __future__ import annotations

import tiktoken

from app.models.chunk import LegalChunk

_ENCODER = tiktoken.get_encoding("cl100k_base")


def _count_chunk_tokens(chunk: LegalChunk) -> int:
    """Return token count of the formatted chunk block."""
    block = (
        f"[Section {chunk.section_number} — {chunk.act_name} ({chunk.act_year})]\n{chunk.content}"
    )
    return len(_ENCODER.encode(block))


def build_context_window(
    chunks: list[LegalChunk],
    max_tokens: int = 4000,
) -> list[LegalChunk]:
    """Return a prefix of *chunks* whose total token count <= *max_tokens*.

    Processes chunks in order (assumed highest-ranked first).  Stops
    accumulating as soon as adding the next chunk would exceed the budget.

    Args:
        chunks: Ranked list of retrieved chunks.
        max_tokens: Maximum total tokens allowed in the context window.

    Returns:
        Subset of chunks that fits within the token budget.
    """
    selected: list[LegalChunk] = []
    total = 0

    for chunk in chunks:
        tokens = _count_chunk_tokens(chunk)
        if total + tokens > max_tokens:
            break
        selected.append(chunk)
        total += tokens

    return selected
