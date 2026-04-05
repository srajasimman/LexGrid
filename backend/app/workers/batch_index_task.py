"""Batch index task — loads all sections for an act and dispatches embed tasks."""

from __future__ import annotations

import structlog

from app.ingestion.chunker import chunk_section
from app.ingestion.loader import load_act_sections
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task
def batch_index_act(act_code: str) -> dict:
    """Load all sections for *act_code*, chunk them, dispatch embed tasks.

    Args:
        act_code: Short act identifier, e.g. 'ipc'.

    Returns:
        Dict with act_code, sections_count, and chunks_count.
    """
    from celery import group
    from app.workers.embed_task import embed_and_index_chunk

    sections = load_act_sections(act_code)
    all_chunks = [chunk for section in sections for chunk in chunk_section(section)]

    task_group = group(embed_and_index_chunk.s(chunk.model_dump()) for chunk in all_chunks)
    task_group.delay()

    result = {
        "act_code": act_code,
        "sections_count": len(sections),
        "chunks_count": len(all_chunks),
    }
    logger.info("batch_index_dispatched", **result)
    return result
