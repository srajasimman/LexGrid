"""Shared Pydantic models for LexGrid."""

from .chunk import ChunkType, LegalChunk, LegalChunkWithEmbedding
from .evaluation import EvalCase, EvalCaseResult, EvalReport
from .metrics import MetricsResponse, QueryMetrics, SystemMetrics
from .query import Citation, QueryRequest, QueryResponse, RetrievedChunk
from .search import SearchRequest, SearchResponse, SectionResult

__all__ = [
    "ChunkType",
    "LegalChunk",
    "LegalChunkWithEmbedding",
    "Citation",
    "QueryRequest",
    "QueryResponse",
    "RetrievedChunk",
    "SearchRequest",
    "SearchResponse",
    "SectionResult",
    "QueryMetrics",
    "SystemMetrics",
    "MetricsResponse",
    "EvalCase",
    "EvalCaseResult",
    "EvalReport",
]
