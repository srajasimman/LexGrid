"""Query cache — SHA256-keyed Redis storage for QueryResponse objects."""

from __future__ import annotations

import hashlib

import redis.asyncio as aioredis

from app.models.query import QueryResponse


def cache_key(query: str, act_codes: list[str] | None) -> str:
    """Return a deterministic Redis key for the (query, act_codes) pair."""
    parts = query.strip().lower() + "|" + ",".join(sorted(act_codes or []))
    return "query:" + hashlib.sha256(parts.encode()).hexdigest()


async def get_cached_query(
    key: str,
    redis: aioredis.Redis,
) -> QueryResponse | None:
    """Deserialise a cached QueryResponse, or return None on miss."""
    raw = await redis.get(key)
    if raw is None:
        return None
    return QueryResponse.model_validate_json(raw)


async def set_cached_query(
    key: str,
    response: QueryResponse,
    ttl: int,
    redis: aioredis.Redis,
) -> None:
    """Serialise *response* to JSON and store with an expiry of *ttl* seconds."""
    await redis.set(key, response.model_dump_json(), ex=ttl)
