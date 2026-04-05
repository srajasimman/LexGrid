"""Embeddings package — OpenAI client, batch processor, and file watcher."""

from app.embeddings.batch_processor import process_chunks_batch
from app.embeddings.client import embed_texts
from app.embeddings.streaming import watch_for_updates

__all__ = [
    "embed_texts",
    "process_chunks_batch",
    "watch_for_updates",
]
