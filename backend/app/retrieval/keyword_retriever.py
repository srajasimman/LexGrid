"""Keyword retriever — PostgreSQL full-text search wrapper."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import LegalChunk
from app.vector_store.store import fts_search


async def keyword_search(
    query_text: str,
    act_codes: list[str] | None,
    top_k: int,
    session: AsyncSession,
) -> list[LegalChunk]:
    """Return top_k chunks matching query_text via PostgreSQL FTS.

    Delegates entirely to vector_store.fts_search.
    """
    return await fts_search(query_text, act_codes, top_k, session)
