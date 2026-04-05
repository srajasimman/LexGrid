"""Ingestion package — load, chunk, and prepare legal acts for embedding."""

from app.ingestion.chunker import chunk_section
from app.ingestion.loader import list_available_acts, load_act_sections
from app.ingestion.pipeline import run_ingestion_pipeline

__all__ = [
    "list_available_acts",
    "load_act_sections",
    "chunk_section",
    "run_ingestion_pipeline",
]
