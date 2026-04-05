"""Search route — direct section lookup by act_code + section_number."""

from __future__ import annotations

from typing import Optional

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import SearchResponse, SectionResult
from app.models.chunk import LegalChunk
from app.normalization.sections import normalize_section_number
from app.vector_store.database import async_get_session
from app.vector_store.store import get_section

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def _to_section_result(chunk: LegalChunk) -> SectionResult:
    """Convert a LegalChunk to a SectionResult for API response."""
    return SectionResult(
        id=chunk.id,
        act_code=chunk.act_code,
        act_name=chunk.act_name,
        act_year=chunk.act_year,
        chapter_number=chunk.chapter_number,
        chapter_title=chunk.chapter_title,
        section_number=chunk.section_number,
        section_title=chunk.section_title,
        content=chunk.content,
        source_url=chunk.source_url,
        relevance_score=None,
    )


@router.get("/", response_model=SearchResponse)
async def search_section(
    act_code: Optional[str] = None,
    section_number: Optional[str] = None,
    session: AsyncSession = Depends(async_get_session),
) -> SearchResponse:
    """Look up a section directly by act_code and section_number."""
    if not act_code or not section_number:
        return SearchResponse(results=[], total=0, query=None)

    normalized_act_code = act_code.strip().lower()
    normalized_section = normalize_section_number(section_number)
    if not normalized_section:
        return SearchResponse(results=[], total=0, query=f"{normalized_act_code} {section_number}")

    chunk = await get_section(normalized_act_code, normalized_section, session)

    if chunk is None:
        logger.info(
            "search_not_found",
            act_code=normalized_act_code,
            section_number=normalized_section,
        )
        return SearchResponse(
            results=[],
            total=0,
            query=f"{normalized_act_code} {normalized_section}",
        )

    result = _to_section_result(chunk)
    return SearchResponse(
        results=[result],
        total=1,
        query=f"{normalized_act_code} {normalized_section}",
    )
