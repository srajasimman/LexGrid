"""Metrics and observability models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class QueryMetrics(BaseModel):
    """Per-query performance metrics."""

    query_hash: str = Field(
        ..., description="SHA256 hash of the query for deduplication"
    )
    latency_ms: int = Field(..., description="Total end-to-end latency in milliseconds")
    retrieval_latency_ms: int = Field(
        ..., description="Retrieval phase latency in milliseconds"
    )
    llm_latency_ms: int = Field(
        ..., description="LLM generation latency in milliseconds"
    )
    cache_hit: bool = Field(..., description="Whether this query was served from cache")
    chunks_retrieved: int = Field(
        ..., description="Number of chunks returned by retrieval"
    )
    chunks_reranked: int = Field(..., description="Number of chunks after re-ranking")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="UTC timestamp of the query"
    )


class SystemMetrics(BaseModel):
    """System-level health and performance snapshot."""

    total_queries: int = Field(
        default=0, description="Total number of queries processed"
    )
    cache_hit_rate: float = Field(
        default=0.0, description="Cache hit rate as a fraction 0-1"
    )
    avg_latency_ms: float = Field(
        default=0.0, description="Average query latency in milliseconds"
    )
    p95_latency_ms: float = Field(
        default=0.0, description="P95 query latency in milliseconds"
    )
    total_sections_indexed: int = Field(
        default=0, description="Total number of sections indexed in pgvector"
    )
    acts_indexed: list[str] = Field(
        default_factory=list, description="List of act codes currently indexed"
    )


class MetricsResponse(BaseModel):
    """Response for /metrics endpoint."""

    system: SystemMetrics = Field(
        ..., description="Aggregate system performance metrics"
    )
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    status: str = Field(default="ok", description="Service status string")
