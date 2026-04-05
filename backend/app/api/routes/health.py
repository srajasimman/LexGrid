"""Health check route — reports DB, Redis, and OpenAI reachability."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.client import ping_redis
from app.config import Settings, get_settings
from app.vector_store.database import async_get_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(async_get_session),
) -> dict:
    """Return service health across DB, Redis, and OpenAI."""
    db_ok = False
    redis_ok = False
    openai_ok = False

    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.warning("health_db_failed", error=str(exc))

    try:
        redis_ok = await ping_redis(settings)
    except Exception as exc:
        logger.warning("health_redis_failed", error=str(exc))

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=10.0,
        )
        openai_ok = True
    except Exception as exc:
        logger.warning("health_openai_failed", error=str(exc))

    status = "ok" if (db_ok and redis_ok and openai_ok) else "degraded"
    return {"status": status, "db": db_ok, "redis": redis_ok, "openai": openai_ok}
