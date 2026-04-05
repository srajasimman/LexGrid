"""Embed task — embeds and upserts a single LegalChunk into pgvector."""

from __future__ import annotations

import asyncio

import structlog

from app.config import get_settings
from app.models.chunk import LegalChunk, LegalChunkWithEmbedding
from app.embeddings.client import embed_texts
from app.vector_store.database import get_session_factory
from app.vector_store.store import upsert_chunk
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5, time_limit=60, soft_time_limit=45)
def embed_and_index_chunk(self, chunk_dict: dict) -> bool:
    """Embed one chunk and upsert it into the vector store.

    Args:
        chunk_dict: Serialised LegalChunk (from model_dump()).

    Returns:
        True on success; retries up to 3 times on failure.
    """

    async def _run() -> bool:
        settings = get_settings()
        chunk = LegalChunk.model_validate(chunk_dict)
        embeddings = await embed_texts([chunk.content], settings)
        enriched = LegalChunkWithEmbedding(**chunk.model_dump(), embedding=embeddings[0])

        from app.vector_store.database import get_engine  # noqa: PLC0415

        factory = get_session_factory()
        async with factory() as session:
            await upsert_chunk(enriched, session)
            await session.commit()

        await get_engine().dispose()  # reset pool before asyncio.run() closes the loop
        logger.info("chunk_indexed", chunk_id=chunk.id)
        return True

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.warning("embed_task_failed", chunk_id=chunk_dict.get("id"), error=str(exc))
        raise self.retry(exc=exc)
