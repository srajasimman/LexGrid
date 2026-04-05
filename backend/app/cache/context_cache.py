"""Context cache — SHA256-keyed Redis storage for retrieved LegalChunk lists."""

from __future__ import annotations

import hashlib
import json

import redis.asyncio as aioredis

from app.models.chunk import LegalChunk


def _context_key(chunk_ids: list[str]) -> str:
    """Derive a cache key from the sorted list of chunk IDs."""
    digest = hashlib.sha256("|".join(sorted(chunk_ids)).encode()).hexdigest()
    return "ctx:" + digest


async def get_cached_context(
    chunk_ids: list[str],
    redis: aioredis.Redis,
) -> list[LegalChunk] | None:
    """Return the cached chunk list, or None on cache miss."""
    raw = await redis.get(_context_key(chunk_ids))
    if raw is None:
        return None
    return [LegalChunk.model_validate(item) for item in json.loads(raw)]


async def set_cached_context(
    chunk_ids: list[str],
    chunks: list[LegalChunk],
    ttl: int,
    redis: aioredis.Redis,
) -> None:
    """Serialise *chunks* to JSON and store with *ttl* second expiry."""
    data = json.dumps([c.model_dump() for c in chunks])
    await redis.set(_context_key(chunk_ids), data, ex=ttl)
