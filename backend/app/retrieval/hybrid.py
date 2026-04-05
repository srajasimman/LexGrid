"""Hybrid retrieval — merges vector + FTS results via Reciprocal Rank Fusion."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import LegalChunk
from app.retrieval.keyword_retriever import keyword_search
from app.retrieval.vector_retriever import vector_search

_RRF_K: int = 60


def _reciprocal_rank_fusion(
    result_lists: list[list[LegalChunk]],
    k: int = _RRF_K,
) -> list[tuple[LegalChunk, float]]:
    """Merge multiple ranked lists using RRF.

    score(d) = Σ  1 / (k + rank_i)  for each list containing d.
    Deduplicates by chunk id, keeping the first-seen LegalChunk object.
    """
    scores: dict[str, float] = {}
    chunks_by_id: dict[str, LegalChunk] = {}

    for ranked_list in result_lists:
        for rank, chunk in enumerate(ranked_list, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
            chunks_by_id.setdefault(chunk.id, chunk)

    return sorted(
        [(chunks_by_id[cid], score) for cid, score in scores.items()],
        key=lambda t: t[1],
        reverse=True,
    )


async def hybrid_retrieve(
    query: str,
    query_embedding: list[float],
    act_codes: list[str] | None,
    top_k: int,
    session: AsyncSession,
) -> list[LegalChunk]:
    """Run vector + keyword search concurrently and fuse with RRF.

    Args:
        query: Raw user query text (for FTS).
        query_embedding: Pre-computed embedding vector (for ANN search).
        act_codes: Optional filter list.
        top_k: Number of final results to return.
        session: Active async DB session.

    Returns:
        Top *top_k* LegalChunk objects ranked by fused RRF score.
    """
    vector_results = await vector_search(query_embedding, act_codes, top_k * 2, session)
    keyword_results = await keyword_search(query, act_codes, top_k * 2, session)

    # Short-circuit: if nothing passes the distance threshold AND no FTS hit,
    # the query is out-of-domain — return empty so the caller skips the LLM.
    if not vector_results and not keyword_results:
        return []

    fused = _reciprocal_rank_fusion([vector_results, keyword_results])
    return [chunk for chunk, _ in fused[:top_k]]
