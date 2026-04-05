"""Store — async upsert, vector similarity search, and FTS via pgvector."""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import ChunkType, LegalChunk, LegalChunkWithEmbedding
from app.vector_store.schema import SectionEmbedding

# Explicit column list for raw SQL SELECT — excludes generated/unmapped columns
# (fts_vector is GENERATED ALWAYS, updated_at has no ORM mapping).
_SELECT_COLS = (
    "id, act_code, act_name, act_year, chapter_number, chapter_title, "
    "section_number, section_title, content, type, source_url, token_count, "
    "embedding, created_at"
)


def _row_to_chunk(mapping: dict) -> LegalChunk:
    """Build a LegalChunk from a raw SQL result row mapping."""
    return LegalChunk(
        id=mapping["id"],
        act_code=mapping["act_code"],
        act_name=mapping["act_name"],
        act_year=mapping["act_year"],
        chapter_number=mapping.get("chapter_number"),
        chapter_title=mapping.get("chapter_title"),
        section_number=mapping["section_number"],
        section_title=mapping.get("section_title"),
        content=mapping["content"],
        chunk_type=ChunkType(mapping["type"]),
        source_url=mapping.get("source_url"),
        token_count=mapping.get("token_count", 0),
    )


def _orm_to_chunk(row: SectionEmbedding) -> LegalChunk:
    """Convert an ORM row back to an immutable LegalChunk."""
    return LegalChunk(
        id=row.id,
        act_code=row.act_code,
        act_name=row.act_name,
        act_year=row.act_year,
        chapter_number=row.chapter_number,
        chapter_title=row.chapter_title,
        section_number=row.section_number,
        section_title=row.section_title,
        content=row.content,
        chunk_type=ChunkType(row.type),
        source_url=row.source_url,
        token_count=row.token_count,
    )


async def upsert_chunk(chunk: LegalChunkWithEmbedding, session: AsyncSession) -> None:
    """Insert or update a section row identified by chunk.id, including its embedding."""
    values = {
        "id": chunk.id,
        "act_code": chunk.act_code,
        "act_name": chunk.act_name,
        "act_year": chunk.act_year,
        "chapter_number": chunk.chapter_number,
        "chapter_title": chunk.chapter_title,
        "section_number": chunk.section_number,
        "section_title": chunk.section_title,
        "content": chunk.content,
        "type": chunk.chunk_type.value,
        "source_url": chunk.source_url,
        "token_count": chunk.token_count,
        "embedding": chunk.embedding,
    }
    stmt = (
        insert(SectionEmbedding)
        .values(**values)
        .on_conflict_do_update(index_elements=["id"], set_=values)
    )
    await session.execute(stmt)


async def similarity_search(
    embedding: list[float],
    act_codes: list[str] | None,
    top_k: int,
    session: AsyncSession,
    max_distance: float = 0.75,
) -> list[LegalChunk]:
    """Return top_k chunks ranked by cosine distance to *embedding*.

    Chunks with cosine distance >= max_distance are excluded — this prevents
    out-of-domain queries (e.g. "quantum physics") from returning spurious
    legal results and triggering unnecessary LLM calls.
    """
    if act_codes:
        sql = (
            f"SELECT {_SELECT_COLS} FROM sections "
            "WHERE act_code = ANY(:codes) "
            "AND embedding <=> CAST(:vec AS vector) < :max_dist "
            "ORDER BY embedding <=> CAST(:vec AS vector) "
            "LIMIT :k"
        )
        params: dict = {
            "vec": str(embedding),
            "k": top_k,
            "codes": act_codes,
            "max_dist": max_distance,
        }
    else:
        sql = (
            f"SELECT {_SELECT_COLS} FROM sections "
            "WHERE embedding <=> CAST(:vec AS vector) < :max_dist "
            "ORDER BY embedding <=> CAST(:vec AS vector) LIMIT :k"
        )
        params = {"vec": str(embedding), "k": top_k, "max_dist": max_distance}

    result = await session.execute(text(sql), params)
    return [_row_to_chunk(dict(r._mapping)) for r in result]


async def fts_search(
    query: str,
    act_codes: list[str] | None,
    top_k: int,
    session: AsyncSession,
) -> list[LegalChunk]:
    """Return top_k chunks matching *query* via PostgreSQL full-text search."""
    if act_codes:
        sql = (
            f"SELECT {_SELECT_COLS} FROM sections "
            "WHERE act_code = ANY(:codes) "
            "AND fts_vector @@ plainto_tsquery('english', :query) "
            "LIMIT :k"
        )
        params: dict = {"query": query, "k": top_k, "codes": act_codes}
    else:
        sql = (
            f"SELECT {_SELECT_COLS} FROM sections "
            "WHERE fts_vector @@ plainto_tsquery('english', :query) LIMIT :k"
        )
        params = {"query": query, "k": top_k}

    result = await session.execute(text(sql), params)
    return [_row_to_chunk(dict(r._mapping)) for r in result]


async def get_section(
    act_code: str,
    section_number: str,
    session: AsyncSession,
) -> LegalChunk | None:
    """Fetch one section by act_code + section_number, or None if not found."""
    stmt = (
        select(SectionEmbedding)
        .where(SectionEmbedding.act_code == act_code)
        .where(SectionEmbedding.section_number == section_number)
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalars().first()
    return _orm_to_chunk(row) if row else None
