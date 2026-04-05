"""Redis async client factory and connectivity check."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.config import Settings


def get_redis_client(settings: Settings) -> aioredis.Redis:
    """Create an async Redis client from REDIS_URL in settings."""
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def ping_redis(settings: Settings) -> bool:
    """Return True if Redis is reachable, False otherwise."""
    client = get_redis_client(settings)
    try:
        return await client.ping()
    except Exception:
        return False
    finally:
        await client.aclose()
