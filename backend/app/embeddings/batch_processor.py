"""Batch processor — embeds LegalChunks and upserts them into pgvector."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.embeddings.client import embed_texts
from app.models.chunk import LegalChunk, LegalChunkWithEmbedding
from app.vector_store.store import upsert_chunk

logger = structlog.get_logger(__name__)


async def process_chunks_batch(
    chunks: list[LegalChunk],
    session: AsyncSession,
    settings: Settings,
) -> int:
    """Embed *chunks* in batches and upsert each into the vector store.

    Args:
        chunks: Chunks to embed and persist.
        session: Active async DB session (caller handles commit lifecycle).
        settings: App settings (batch size, model name, API key).

    Returns:
        Total number of chunks successfully upserted.
    """
    batch_size = settings.embedding_batch_size
    upserted = 0

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [c.content for c in batch]

        embeddings = await embed_texts(texts, settings)

        for chunk, embedding in zip(batch, embeddings):
            enriched = LegalChunkWithEmbedding(**chunk.model_dump(), embedding=embedding)
            await upsert_chunk(enriched, session)
            upserted += 1

        await session.commit()
        logger.info(
            "batch_processed",
            start=start,
            count=len(batch),
            total_so_far=upserted,
        )

    logger.info("embedding_complete", total_upserted=upserted)
    return upserted
