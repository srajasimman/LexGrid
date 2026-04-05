"""Direct section search models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Direct section lookup request."""

    act_code: Optional[str] = Field(None, description="Act code, e.g. ipc")
    section_number: Optional[str] = Field(None, description="Section number, e.g. 120A")
    query: Optional[str] = Field(None, description="Free-text search query")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum number of results to return"
    )


class SectionResult(BaseModel):
    """A single section result from direct lookup."""

    model_config = {"frozen": True}

    id: str = Field(..., description="Unique section ID")
    act_code: str = Field(..., description="Short act code")
    act_name: str = Field(..., description="Full act name")
    act_year: str = Field(..., description="Year of the act")
    chapter_number: Optional[str] = Field(None, description="Chapter number")
    chapter_title: Optional[str] = Field(None, description="Chapter title")
    section_number: str = Field(..., description="Section number")
    section_title: Optional[str] = Field(None, description="Section title")
    content: str = Field(..., description="Full text content of the section")
    source_url: Optional[str] = Field(None, description="Source URL")
    relevance_score: Optional[float] = Field(
        None, description="Relevance score 0-1, present for FTS results"
    )


class SearchResponse(BaseModel):
    """Response for section search."""

    results: list[SectionResult] = Field(..., description="List of matching sections")
    total: int = Field(..., description="Total number of matching sections")
    query: Optional[str] = Field(None, description="The search query used, if any")
