"""LexGrid FastAPI application — lifespan wiring, router inclusion, middleware."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI

from app.api.middleware import register_middleware
from app.api.routes import health, metrics, query, search, source
from app.cache.client import get_redis_client
from app.config import get_settings
from app.vector_store.database import get_engine

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialise shared resources on startup; clean up on shutdown."""
    settings = get_settings()

    # Warm up DB connection pool
    engine = get_engine()
    logger.info("db_pool_ready", url=settings.database_url.split("@")[-1])

    # Verify Redis connectivity
    redis = get_redis_client(settings)
    try:
        await redis.ping()
        logger.info("redis_ready", url=settings.redis_url)
    except Exception as exc:
        logger.warning("redis_unavailable", error=str(exc))

    yield

    # Graceful shutdown
    await redis.aclose()
    await engine.dispose()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="LexGrid",
        description="Legal RAG API for Indian Bare Acts",
        version="0.1.0",
        lifespan=lifespan,
    )

    register_middleware(app)

    app.include_router(query.router)
    app.include_router(search.router)
    app.include_router(source.router)
    app.include_router(health.router)
    app.include_router(metrics.router)

    return app


app = create_app()
