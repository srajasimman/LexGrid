"""Query route — full RAG pipeline: cache → retrieve → rerank → LLM → cache."""

from __future__ import annotations

import time
from typing import Optional

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.client import get_redis_client
from app.cache.query_cache import cache_key, get_cached_query, set_cached_query
from app.config import Settings, get_settings
from app.embeddings.client import embed_texts
from app.llm.client import generate_answer
from app.models.query import QueryRequest, QueryResponse, RetrievedChunk
from app.retrieval.hybrid import hybrid_retrieve
from app.retrieval.query_intelligence import parse_query
from app.retrieval.reranker import rerank_chunks
from app.vector_store.database import async_get_session
from app.vector_store.store import get_section

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


async def _get_redis(settings: Settings = Depends(get_settings)) -> aioredis.Redis:
    """FastAPI dependency that yields a Redis client."""
    return get_redis_client(settings)


def _build_retrieved_chunks(chunks, method: str) -> list[RetrievedChunk]:
    """Convert LegalChunk list to RetrievedChunk list for the response."""
    return [
        RetrievedChunk(
            id=c.id,
            act_code=c.act_code,
            act_name=c.act_name,
            section_number=c.section_number,
            section_title=c.section_title,
            content=c.content[:500],
            score=1.0,
            retrieval_method=method,
        )
        for c in chunks
    ]


@router.post("/", response_model=QueryResponse)
async def run_query(
    request: QueryRequest,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(async_get_session),
    redis: aioredis.Redis = Depends(_get_redis),
) -> QueryResponse:
    """Execute full RAG pipeline and return grounded legal answer."""
    start_ms = time.time()
    act_codes: Optional[list[str]] = [request.act_filter] if request.act_filter else None

    parsed = parse_query(request.query)

    # Direct section lookup short-circuit
    if parsed["direct_lookup"]:
        chunk = await get_section(parsed["act_code"], parsed["section_number"], session)
        chunks = [chunk] if chunk else []
        retrieval_method = "direct"
    else:
        # Check cache first
        key = cache_key(request.query, act_codes)
        if request.use_cache:
            cached = await get_cached_query(key, redis)
            if cached is not None:
                cached_with_hit = cached.model_copy(update={"cache_hit": True})
                logger.info("cache_hit", query=request.query[:80])
                return cached_with_hit

        # Embed query + hybrid retrieval
        embeddings = await embed_texts([request.query], settings)
        query_embedding = embeddings[0]
        chunks = await hybrid_retrieve(
            request.query, query_embedding, act_codes, settings.top_k_retrieval, session
        )
        chunks = await rerank_chunks(request.query, chunks, settings.top_k_rerank, settings)
        retrieval_method = "hybrid"

    answer, citations = await generate_answer(request.query, chunks, settings)
    latency = int((time.time() - start_ms) * 1000)

    response = QueryResponse(
        answer=answer,
        citations=citations,
        retrieved_chunks=_build_retrieved_chunks(chunks, retrieval_method),
        query=request.query,
        cache_hit=False,
        latency_ms=latency,
    )

    # Store in cache for future hits (skip for direct lookups)
    if not parsed["direct_lookup"] and request.use_cache:
        await set_cached_query(key, response, settings.cache_ttl_seconds, redis)

    logger.info("query_complete", latency_ms=latency, chunks=len(chunks))
    return response
