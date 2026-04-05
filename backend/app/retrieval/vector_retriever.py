"""Vector retriever — thin wrapper around pgvector similarity_search."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import LegalChunk
from app.vector_store.store import similarity_search


async def vector_search(
    query_embedding: list[float],
    act_codes: list[str] | None,
    top_k: int,
    session: AsyncSession,
) -> list[LegalChunk]:
    """Return top_k chunks ranked by cosine distance to query_embedding.

    Delegates entirely to vector_store.similarity_search.
    """
    return await similarity_search(query_embedding, act_codes, top_k, session)
