"""Pipeline — orchestrates load → chunk for ingestion into pgvector store."""

from __future__ import annotations

import structlog

from app.ingestion.chunker import chunk_section
from app.ingestion.loader import list_available_acts, load_act_sections
from app.models.chunk import LegalChunk

logger = structlog.get_logger(__name__)


def run_ingestion_pipeline(
    act_codes: list[str] | None = None,
) -> list[LegalChunk]:
    """Load and chunk all (or specified) legal acts.

    Args:
        act_codes: Optional list of act codes to process, e.g. ['ipc', 'crpc'].
                   When None, all acts found under legal-acts/ are processed.

    Returns:
        Flat list of LegalChunk objects from every section of every act.
    """
    codes = act_codes if act_codes is not None else list_available_acts()
    all_chunks: list[LegalChunk] = []

    for act_code in codes:
        try:
            sections = load_act_sections(act_code)
        except FileNotFoundError:
            logger.warning("act_sections_not_found", act_code=act_code)
            continue

        act_chunks: list[LegalChunk] = []
        for section in sections:
            act_chunks.extend(chunk_section(section))

        logger.info(
            "act_ingested",
            act_code=act_code,
            section_count=len(sections),
            chunk_count=len(act_chunks),
        )
        all_chunks.extend(act_chunks)

    logger.info(
        "pipeline_complete",
        act_count=len(codes),
        total_chunks=len(all_chunks),
    )
    return all_chunks
