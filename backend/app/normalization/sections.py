"""Utilities for normalizing legal section identifiers."""

from __future__ import annotations

import re


def normalize_section_number(section_number: str) -> str:
    """Normalize section number into canonical DB lookup form.

    Examples:
    - "149" -> "149"
    - "120A" -> "120A"
    - "120-a" -> "120A"
    - "Section 149" -> "149"
    """
    raw = section_number.strip()
    raw = re.sub(r"^section\s+", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw)
    if not cleaned:
        return ""

    if cleaned.isdigit():
        return cleaned

    # Keep numeric prefix + uppercase alpha suffix form commonly used in DB
    match = re.match(r"^(\d+)([A-Za-z]+)$", cleaned)
    if match:
        num, suffix = match.groups()
        return f"{num}{suffix.upper()}"

    # Fallback: uppercase all alpha chars while preserving digits order
    return "".join(ch.upper() if ch.isalpha() else ch for ch in cleaned)
