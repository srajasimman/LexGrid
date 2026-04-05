"""Reindex task — re-embeds sections from specific JSON file paths."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from app.ingestion.chunker import chunk_section
from app.workers.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task
def reindex_updated_sections(file_paths: list[str]) -> dict:
    """Reload and re-embed sections from the specified JSON files.

    Args:
        file_paths: Absolute or relative paths to section JSON files.

    Returns:
        Dict with count of updated chunks.
    """
    from celery import group
    from app.workers.embed_task import embed_and_index_chunk

    all_chunks = []
    for path_str in file_paths:
        path = Path(path_str)
        if not path.exists():
            logger.warning("reindex_file_missing", path=path_str)
            continue
        with path.open(encoding="utf-8") as fh:
            section = json.load(fh)
        all_chunks.extend(chunk_section(section))

    if all_chunks:
        task_group = group(embed_and_index_chunk.s(chunk.model_dump()) for chunk in all_chunks)
        task_group.delay()

    result = {"updated": len(all_chunks)}
    logger.info("reindex_dispatched", **result)
    return result
