"""CLI: Run the LexGrid evaluation suite and output a Precision@K / Recall@K / MRR report."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import click

# Allow running as: python scripts/evaluate.py from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.evaluation.reporter import log_failures, save_report  # noqa: E402
from app.evaluation.runner import run_evaluation  # noqa: E402
from app.evaluation.test_cases import EVAL_CASES  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--api-url",
    default="http://localhost:8000",
    show_default=True,
    help="Base URL of the running LexGrid API.",
)
@click.option(
    "--output",
    default="eval_report.json",
    show_default=True,
    type=click.Path(dir_okay=False, writable=True),
    help="Path where the JSON report will be saved.",
)
def main(api_url: str, output: str) -> None:
    """Run all evaluation test cases against the LexGrid API and print a summary."""
    logger.info("Running %d test cases against %s …", len(EVAL_CASES), api_url)

    report = asyncio.run(run_evaluation(EVAL_CASES, api_url))

    output_path = Path(output)
    save_report(report, output_path)
    log_failures(report)

    sep = "=" * 60
    logger.info(sep)
    logger.info("  LexGrid Evaluation Report  —  run %s", report.run_id[:8])
    logger.info(sep)
    logger.info("  Total cases : %d", report.total_cases)
    logger.info("  Passed      : %d  (%.0f%%)", report.passed, report.pass_rate * 100)
    logger.info("  Failed      : %d", report.failed)
    logger.info("  Mean P@5    : %.3f", report.mean_precision_at_k)
    logger.info("  Mean R@5    : %.3f", report.mean_recall_at_k)
    logger.info("  MRR         : %.3f", report.mrr)
    logger.info("  Legal Acc.  : %.3f", report.mean_legal_accuracy)
    logger.info(sep)
    logger.info("Report saved → %s", output_path.resolve())

    # Non-zero exit if majority of cases fail
    if report.pass_rate < 0.5:
        sys.exit(1)


if __name__ == "__main__":
    main()
