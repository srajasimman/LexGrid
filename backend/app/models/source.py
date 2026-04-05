"""Canonical markdown source response models."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SectionSourceResponse(BaseModel):
    """Response payload for canonical markdown source lookup."""

    act_code: str = Field(..., description="Short act code")
    section_number: str = Field(..., description="Requested section number")
    normalized_section_number: str = Field(..., description="Normalized section identifier")
    source_markdown_found: bool = Field(..., description="True if markdown source was found")
    source_markdown: Optional[str] = Field(None, description="Markdown source content")
    source_markdown_path: Optional[str] = Field(
        None,
        description="Path to markdown source relative to legal-acts root",
    )
