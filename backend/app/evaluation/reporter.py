"""Reporter — saves EvalReport to JSON and logs low-precision failures."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models.evaluation import EvalReport

logger = logging.getLogger(__name__)


def save_report(report: EvalReport, output_path: Path) -> None:
    """Serialise the EvalReport to a JSON file at *output_path*.

    Creates parent directories if they do not exist.

    Args:
        report:      The completed evaluation report.
        output_path: Destination file path (will be overwritten if it exists).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.info("Evaluation report saved → %s", output_path)


def log_failures(report: EvalReport) -> None:
    """Log every case where Precision@5 < 0.5 at WARNING level.

    Args:
        report: The completed evaluation report.
    """
    low_precision = [r for r in report.results if r.precision_at_k < 0.5]
    if not low_precision:
        logger.info("All cases passed Precision@5 >= 0.5 — no failures to report.")
        return

    logger.warning(
        "⚠  %d/%d cases have Precision@5 < 0.5:",
        len(low_precision),
        report.total_cases,
    )
    for result in low_precision:
        logger.warning(
            "  [%s] %s | P@5=%.2f | RR=%.2f | reason=%s",
            result.case_id,
            result.query[:60],
            result.precision_at_k,
            result.reciprocal_rank,
            result.failure_reason or "—",
        )
