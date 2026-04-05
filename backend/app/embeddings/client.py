"""OpenAI embedding client with tenacity retry and batch splitting."""

from __future__ import annotations

import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings


def _make_retry_decorator():
    return retry(
        retry=retry_if_exception_type((openai.RateLimitError, openai.APIError)),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )


async def _embed_batch(
    batch: list[str],
    client: AsyncOpenAI,
    model: str,
) -> list[list[float]]:
    """Embed a single batch; retried on rate-limit / API errors."""

    @_make_retry_decorator()
    async def _call() -> list[list[float]]:
        response = await client.embeddings.create(model=model, input=batch)
        return [item.embedding for item in response.data]

    return await _call()


async def embed_texts(
    texts: list[str],
    settings: Settings,
) -> list[list[float]]:
    """Return one 1536-dim embedding per input text.

    Splits *texts* into batches of settings.embedding_batch_size and
    issues one OpenAI call per batch. Retries on rate-limit errors with
    exponential back-off (min=1 s, max=60 s, 5 attempts).

    Args:
        texts: Raw strings to embed.
        settings: App settings (provides api_key, model, batch_size).

    Returns:
        List of float vectors in the same order as *texts*.
    """
    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=30.0,  # 30s hard timeout per request — prevents hung workers
    )
    batch_size = settings.embedding_batch_size
    results: list[list[float]] = []

    async with client:
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            embeddings = await _embed_batch(batch, client, settings.embedding_model)
            results.extend(embeddings)

    return results
