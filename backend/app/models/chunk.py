"""Legal chunk models — core data unit for the RAG pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    SECTION = "section"
    CLAUSE = "clause"
    EXPLANATION = "explanation"
    AMENDMENT = "amendment"


class LegalChunk(BaseModel):
    """A single indexed unit of legal text with full metadata."""

    model_config = {"frozen": True}

    id: str = Field(..., description="Unique chunk ID, e.g. ipc-120A-section")
    act_code: str = Field(..., description="Short act code, e.g. ipc, bns, crpc")
    act_name: str = Field(..., description="Full act name, e.g. Indian Penal Code")
    act_year: str = Field(..., description="Year of the act, e.g. 1860")
    chapter_number: Optional[str] = Field(None, description="Chapter number")
    chapter_title: Optional[str] = Field(None, description="Chapter title")
    section_number: str = Field(..., description="Section number, e.g. 120A")
    section_title: Optional[str] = Field(None, description="Section title")
    content: str = Field(..., description="Text content of this chunk")
    chunk_type: ChunkType = Field(default=ChunkType.SECTION)
    source_url: Optional[str] = Field(None, description="Source URL")
    token_count: int = Field(default=0, description="Approximate token count")

    def chunk_id(self) -> str:
        """Generate canonical chunk ID."""
        return f"{self.act_code}-{self.section_number}-{self.chunk_type.value}"


class LegalChunkWithEmbedding(LegalChunk):
    """LegalChunk with its embedding vector attached."""

    model_config = {"frozen": False}  # mutable to attach embedding

    embedding: Optional[list[float]] = Field(
        None, description="1536-dim OpenAI embedding"
    )
