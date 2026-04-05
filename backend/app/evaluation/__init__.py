"""Evaluation package — automated RAG evaluation with Precision@K, Recall@K, MRR."""

from app.evaluation.metrics import (
    legal_accuracy_score,
    mrr,
    precision_at_k,
    recall_at_k,
)
from app.evaluation.reporter import log_failures, save_report
from app.evaluation.runner import run_evaluation
from app.evaluation.test_cases import EVAL_CASES

__all__ = [
    "EVAL_CASES",
    "legal_accuracy_score",
    "log_failures",
    "mrr",
    "precision_at_k",
    "recall_at_k",
    "run_evaluation",
    "save_report",
]
