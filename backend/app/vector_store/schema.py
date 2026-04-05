"""Schema — SQLAlchemy ORM model for the sections table with pgvector."""

from __future__ import annotations

from sqlalchemy import Computed, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class SectionEmbedding(Base):
    """ORM representation of the `sections` table.

    Columns mirror LegalChunk fields plus a 1536-dim pgvector embedding
    and a GENERATED ALWAYS tsvector column for full-text search.
    """

    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    act_code: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    act_name: Mapped[str] = mapped_column(Text, nullable=False)
    act_year: Mapped[str] = mapped_column(Text, nullable=False)
    chapter_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    chapter_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    section_number: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False, default="section")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 1536 dimensions for text-embedding-3-small
    embedding: Mapped[list | None] = mapped_column(Vector(1536), nullable=True)
    # GENERATED ALWAYS AS column — DB auto-populates; never write from Python
    fts_vector: Mapped[object | None] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(section_title, '')), 'A') || "
            "setweight(to_tsvector('english', coalesce(act_name, '')), 'B') || "
            "setweight(to_tsvector('english', coalesce(content, '')), 'C')",
            persisted=True,
        ),
        nullable=True,
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
