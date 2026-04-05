"""Query request/response models for the RAG pipeline."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A legal citation extracted from an LLM response."""

    model_config = {"frozen": True}

    act_code: str = Field(..., description="Short act code, e.g. ipc")
    act_name: str = Field(..., description="Full act name, e.g. Indian Penal Code")
    section_number: str = Field(..., description="Section number, e.g. 120A")
    section_title: Optional[str] = Field(None, description="Section title")
    source_url: Optional[str] = Field(
        None, description="Source URL for the cited section"
    )

    def __str__(self) -> str:
        return f"Section {self.section_number}, {self.act_name}"


class QueryRequest(BaseModel):
    """Incoming legal query from the user."""

    query: str = Field(..., min_length=3, max_length=2000, description="Legal question")
    act_filter: Optional[str] = Field(None, description="Filter by act code, e.g. ipc")
    top_k: int = Field(
        default=5, ge=1, le=20, description="Number of results to return"
    )
    use_cache: bool = Field(default=True, description="Whether to use Redis cache")


class RetrievedChunk(BaseModel):
    """A retrieved chunk with relevance score."""

    model_config = {"frozen": True}

    id: str = Field(..., description="Unique chunk ID")
    act_code: str = Field(..., description="Short act code")
    act_name: str = Field(..., description="Full act name")
    section_number: str = Field(..., description="Section number")
    section_title: Optional[str] = Field(None, description="Section title")
    content: str = Field(..., description="Text content of this chunk")
    score: float = Field(..., description="Relevance score 0-1")
    retrieval_method: str = Field(..., description="vector | keyword | hybrid")


class QueryResponse(BaseModel):
    """Full RAG response with answer and citations."""

    answer: str = Field(..., description="Grounded legal answer")
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    query: str = Field(..., description="Original query string")
    cache_hit: bool = Field(
        default=False, description="Whether this response was served from cache"
    )
    latency_ms: int = Field(
        default=0, description="Total query latency in milliseconds"
    )
