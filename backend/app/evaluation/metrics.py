"""Metrics — Precision@K, Recall@K, MRR, and legal accuracy computation."""

from __future__ import annotations
import re

# Human-readable aliases for each act code used in section IDs.
# The LLM cites acts by their full names, so we match either the short code
# or any common variant of the full name (case-insensitive).
_ACT_ALIASES: dict[str, list[str]] = {
    "ipc": ["ipc", "indian penal code", "i.p.c"],
    "crpc": ["crpc", "code of criminal procedure", "c.r.p.c", "cr.p.c"],
    "bns": ["bns", "bharatiya nyaya sanhita"],
    "cpc": ["cpc", "code of civil procedure", "c.p.c"],
    "iea": ["iea", "indian evidence act"],
    "hma": ["hma", "hindu marriage act"],
    "ida": ["ida", "indian divorce act"],
    "mva": ["mva", "motor vehicles act"],
    "nia": ["nia", "national investigation agency act"],
}


def _parse_section_id(section_id: str) -> tuple[str, str] | None:
    """Extract (act_code, section_number) from a DB section ID.

    Expected format: ``{act_code}-{section_number}-section``, e.g. ``ipc-300-section``.
    Returns None if the format does not match.
    """
    parts = section_id.split("-")
    if len(parts) < 3 or parts[-1] != "section":
        return None
    act_code = parts[0].lower()
    section_number = "-".join(parts[1:-1])  # handles multi-part like "120A"
    return act_code, section_number


def _is_cited(answer_lower: str, act_code: str, section_number: str) -> bool:
    """Return True when both the section number and the act are mentioned in the answer.

    The section number must appear as a standalone token (e.g. "300" in "Section 300"
    but not inside "1300").  The act must match at least one alias.
    """
    # Section number present as a word boundary token
    section_pattern = rf"\bsection\s+{re.escape(section_number)}\b"
    if not re.search(section_pattern, answer_lower, re.IGNORECASE):
        return False

    # At least one act alias present anywhere in the answer
    aliases = _ACT_ALIASES.get(act_code, [act_code])
    return any(alias in answer_lower for alias in aliases)


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of top-k retrieved items that are relevant.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant:  Ground-truth relevant chunk IDs.
        k:         Cut-off rank.

    Returns:
        Precision@k in [0.0, 1.0].
    """
    if k <= 0:
        return 0.0
    top_k = set(retrieved[:k])
    hits = len(top_k & set(relevant))
    return hits / k


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Fraction of relevant items found in the top-k retrieved results.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant:  Ground-truth relevant chunk IDs.
        k:         Cut-off rank.

    Returns:
        Recall@k in [0.0, 1.0].
    """
    if not relevant:
        return 1.0  # vacuously true — nothing expected, nothing missed
    top_k = set(retrieved[:k])
    hits = len(top_k & set(relevant))
    return hits / len(set(relevant))


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    """Mean Reciprocal Rank — reciprocal of rank of first relevant result.

    Args:
        retrieved: Ordered list of retrieved chunk IDs.
        relevant:  Ground-truth relevant chunk IDs.

    Returns:
        MRR contribution in [0.0, 1.0].
    """
    relevant_set = set(relevant)
    for i, item in enumerate(retrieved):
        if item in relevant_set:
            return 1.0 / (i + 1)
    return 0.0


def legal_accuracy_score(answer: str, expected_section_ids: list[str]) -> float:
    """Fraction of expected section IDs explicitly cited in the answer text.

    Matches human-readable citation patterns like "Section 300 IPC" or
    "Section 436, Code of Criminal Procedure" rather than raw DB IDs.
    Falls back to raw substring match when the ID cannot be parsed.

    Args:
        answer:               LLM-generated answer string.
        expected_section_ids: Section IDs in ``{act_code}-{number}-section`` format.

    Returns:
        Score in [0.0, 1.0]; 1.0 when expected_section_ids is empty.
    """
    if not expected_section_ids:
        return 1.0
    lowered = answer.lower()
    hits = 0
    for sid in expected_section_ids:
        parsed = _parse_section_id(sid)
        if parsed is not None:
            act_code, section_number = parsed
            if _is_cited(lowered, act_code, section_number):
                hits += 1
        else:
            # Fallback: raw substring match for unexpected ID formats
            if sid.lower() in lowered:
                hits += 1
    return hits / len(expected_section_ids)
