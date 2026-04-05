"""Reranker — uses gpt-4o-mini to re-order retrieved chunks by relevance."""

from __future__ import annotations

import json
import re

import structlog
from openai import AsyncOpenAI

from app.config import Settings
from app.models.chunk import LegalChunk

logger = structlog.get_logger(__name__)

_INDEX_LIST_RE = re.compile(r"\[[\d,\s]+\]")


def _build_rerank_prompt(query: str, chunks: list[LegalChunk]) -> str:
    """Format chunk list into a concise reranking prompt."""
    lines = [f"Query: {query}\n\nChunks (index, section, content):"]
    for i, c in enumerate(chunks):
        snippet = c.content[:200].replace("\n", " ")
        lines.append(f"{i}: [Sec {c.section_number}, {c.act_code}] {snippet}")
    lines.append(
        "\nReturn ONLY a JSON array of indices ordered by legal relevance "
        "(most relevant first), e.g. [2,0,1]."
    )
    return "\n".join(lines)


async def rerank_chunks(
    query: str,
    chunks: list[LegalChunk],
    top_k: int,
    settings: Settings,
) -> list[LegalChunk]:
    """Re-order *chunks* by relevance using the LLM; falls back to original order.

    Args:
        query: User query for relevance scoring.
        chunks: Pre-retrieved candidate chunks.
        top_k: Number of top results to return.
        settings: App settings (model, API key).

    Returns:
        Up to *top_k* chunks in descending relevance order.
    """
    if not chunks:
        return []

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    prompt = _build_rerank_prompt(query, chunks)

    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
        )
        raw = response.choices[0].message.content or ""
        match = _INDEX_LIST_RE.search(raw)
        if match:
            indices = json.loads(match.group())
            reordered = [chunks[i] for i in indices if 0 <= i < len(chunks)]
            return reordered[:top_k]
    except Exception as exc:
        logger.warning("rerank_failed", error=str(exc))

    return chunks[:top_k]
