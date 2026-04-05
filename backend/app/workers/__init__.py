"""Celery workers package — import tasks so autodiscover finds them."""

from app.workers import batch_index_task, embed_task, reindex_task  # noqa: F401
