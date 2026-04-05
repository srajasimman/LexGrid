"""Evaluation framework models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """A single evaluation test case."""

    model_config = {"frozen": True}

    id: str = Field(..., description="Unique test case ID")
    query: str = Field(..., description="The legal question to evaluate")
    expected_section_ids: list[str] = Field(
        ...,
        description="List of section IDs that MUST appear in retrieved results",
    )
    expected_acts: list[str] = Field(
        ...,
        description="Act codes that should be referenced, e.g. ['ipc']",
    )
    query_type: str = Field(
        ...,
        description="direct | comparative | procedural | negative | cross_act",
    )
    expected_answer_contains: Optional[list[str]] = Field(
        None,
        description="Keywords/phrases that must appear in the answer",
    )
    should_find_answer: bool = Field(
        default=True,
        description="If False, system should say it cannot find the answer",
    )


class EvalCaseResult(BaseModel):
    """Result of running one evaluation case."""

    case_id: str = Field(..., description="ID of the evaluated test case")
    query: str = Field(..., description="The evaluated query")
    query_type: str = Field(..., description="Type of the query")
    retrieved_ids: list[str] = Field(
        ..., description="Chunk IDs returned by the retrieval pipeline"
    )
    answer: str = Field(..., description="The LLM-generated answer")
    precision_at_k: float = Field(..., description="Precision@K for this case")
    recall_at_k: float = Field(..., description="Recall@K for this case")
    reciprocal_rank: float = Field(
        ..., description="Reciprocal rank (MRR contribution)"
    )
    legal_accuracy: float = Field(..., description="Legal accuracy score 0-1")
    passed: bool = Field(
        ..., description="Whether this case passed all acceptance criteria"
    )
    failure_reason: Optional[str] = Field(
        None, description="Reason for failure, if any"
    )
    latency_ms: int = Field(
        default=0, description="End-to-end latency for this case in milliseconds"
    )


class EvalReport(BaseModel):
    """Full evaluation report across all test cases."""

    run_id: str = Field(..., description="Unique ID for this evaluation run")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the evaluation was run",
    )
    total_cases: int = Field(..., description="Total number of test cases evaluated")
    passed: int = Field(..., description="Number of test cases that passed")
    failed: int = Field(..., description="Number of test cases that failed")
    mean_precision_at_k: float = Field(
        ..., description="Mean Precision@K across all cases"
    )
    mean_recall_at_k: float = Field(..., description="Mean Recall@K across all cases")
    mrr: float = Field(..., description="Mean Reciprocal Rank across all cases")
    mean_legal_accuracy: float = Field(
        ..., description="Mean legal accuracy score across all cases"
    )
    pass_rate: float = Field(..., description="Fraction of cases that passed (0-1)")
    results: list[EvalCaseResult] = Field(..., description="Per-case results")
    failure_cases: list[EvalCaseResult] = Field(
        default_factory=list,
        description="Subset of results that failed — for quick triage",
    )
