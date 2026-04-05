"""Prometheus metrics route — exposes prometheus_client plaintext output."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/")
async def prometheus_metrics() -> Response:
    """Return Prometheus-formatted plaintext metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
