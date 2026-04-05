"""Source route — canonical markdown source lookup by act_code + section_number."""

from __future__ import annotations

import re

from fastapi import APIRouter

from app.config import get_settings
from app.ingestion.markdown_source import load_section_markdown
from app.models.source import SectionSourceResponse
from app.normalization.sections import normalize_section_number

router = APIRouter(prefix="/source", tags=["source"])


def _normalize_section_number(section_number: str) -> str:
    """Normalize section number to canonical lookup token."""
    canonical = normalize_section_number(section_number)
    compact = canonical.lower()
    compact = re.sub(r"[^a-z0-9-]", "", compact)
    return re.sub(r"-+", "-", compact).strip("-")


@router.get("/", response_model=SectionSourceResponse)
async def get_section_source(
    act_code: str,
    section_number: str,
) -> SectionSourceResponse:
    """Get canonical markdown source for a section if available."""
    settings = get_settings()
    normalized_section = _normalize_section_number(section_number)
    normalized_act_code = act_code.strip().lower()

    found, markdown, path = load_section_markdown(
        legal_acts_root=settings.legal_acts_path,
        act_code=normalized_act_code,
        section_number=section_number,
    )

    return SectionSourceResponse(
        act_code=normalized_act_code,
        section_number=section_number,
        normalized_section_number=normalized_section,
        source_markdown_found=found,
        source_markdown=markdown if found else None,
        source_markdown_path=path if found else None,
    )
