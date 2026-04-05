"""Runner — executes evaluation suite over all test cases via the live API."""

from __future__ import annotations

import time
import uuid
from datetime import datetime

import httpx

from app.evaluation.metrics import (
    legal_accuracy_score,
    mrr,
    precision_at_k,
    recall_at_k,
)
from app.models.evaluation import EvalCase, EvalCaseResult, EvalReport


_K = 5  # cut-off rank used for Precision@K and Recall@K


async def _run_single(
    case: EvalCase,
    api_url: str,
    client: httpx.AsyncClient,
) -> EvalCaseResult:
    """Call POST /query for one test case and compute its metrics."""
    payload = {
        "query": case.query,
        "top_k": _K,
        "use_cache": False,
    }
    if case.expected_acts:
        payload["act_filter"] = case.expected_acts[0]

    t0 = time.monotonic()
    try:
        resp = await client.post(f"{api_url.rstrip('/')}/query/", json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        # Negative cases (should_find_answer=False) pass even on API error —
        # getting no answer is the correct outcome.
        exc_passed = not case.should_find_answer
        return EvalCaseResult(
            case_id=case.id,
            query=case.query,
            query_type=case.query_type,
            retrieved_ids=[],
            answer="",
            precision_at_k=0.0,
            recall_at_k=0.0,
            reciprocal_rank=0.0,
            legal_accuracy=0.0,
            passed=exc_passed,
            failure_reason=None if exc_passed else str(exc),
            latency_ms=elapsed,
        )

    elapsed = int((time.monotonic() - t0) * 1000)
    retrieved_ids = [c["id"] for c in data.get("retrieved_chunks", [])]
    answer: str = data.get("answer", "")

    p_k = precision_at_k(retrieved_ids, case.expected_section_ids, _K)
    r_k = recall_at_k(retrieved_ids, case.expected_section_ids, _K)
    rr = mrr(retrieved_ids, case.expected_section_ids)
    la = legal_accuracy_score(answer, case.expected_section_ids)

    # Pass = at least one expected section found in top-k (recall > 0)
    # OR negative query with empty expectation (should_find_answer=False)
    passed = (rr > 0.0) if case.expected_section_ids else (not case.should_find_answer)
    failure_reason: str | None = None if passed else f"mrr=0.00 retrieved={retrieved_ids[:3]}"

    return EvalCaseResult(
        case_id=case.id,
        query=case.query,
        query_type=case.query_type,
        retrieved_ids=retrieved_ids,
        answer=answer,
        precision_at_k=p_k,
        recall_at_k=r_k,
        reciprocal_rank=rr,
        legal_accuracy=la,
        passed=passed,
        failure_reason=failure_reason,
        latency_ms=elapsed,
    )


async def run_evaluation(test_cases: list[EvalCase], api_url: str) -> EvalReport:
    """Run all test cases against the live API and return a full EvalReport."""
    async with httpx.AsyncClient() as client:
        results = [await _run_single(c, api_url, client) for c in test_cases]

    n = len(results)
    passed_count = sum(1 for r in results if r.passed)

    return EvalReport(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        total_cases=n,
        passed=passed_count,
        failed=n - passed_count,
        mean_precision_at_k=sum(r.precision_at_k for r in results) / n if n else 0.0,
        mean_recall_at_k=sum(r.recall_at_k for r in results) / n if n else 0.0,
        mrr=sum(r.reciprocal_rank for r in results) / n if n else 0.0,
        mean_legal_accuracy=sum(r.legal_accuracy for r in results) / n if n else 0.0,
        pass_rate=passed_count / n if n else 0.0,
        results=results,
        failure_cases=[r for r in results if not r.passed],
    )
