"""Vector store package — pgvector schema, async CRUD, and search."""

from app.vector_store.database import async_get_session, get_engine, get_session_factory
from app.vector_store.schema import Base, SectionEmbedding
from app.vector_store.store import fts_search, get_section, similarity_search, upsert_chunk

__all__ = [
    "Base",
    "SectionEmbedding",
    "get_engine",
    "get_session_factory",
    "async_get_session",
    "upsert_chunk",
    "similarity_search",
    "fts_search",
    "get_section",
]
