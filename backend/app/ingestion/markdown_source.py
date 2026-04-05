"""Markdown source loader for canonical section documents."""

from __future__ import annotations

import re
from pathlib import Path

from app.normalization.sections import normalize_section_number

_VALID_ACT_CODE = re.compile(r"^[a-z0-9_-]+$")
_VALID_SECTION = re.compile(r"^[a-z0-9-]+$")


def _normalize_act_code(act_code: str) -> str:
    """Normalize act_code for file-system lookups."""
    return act_code.strip().lower()


def _normalize_section_number(section_number: str) -> str:
    """Normalize section_number for markdown file naming.

    Examples:
    - "149" -> "149"
    - "120A" -> "120a"
    - "120 A" -> "120-a"
    - "Section 149" -> "149"
    """
    normalized = normalize_section_number(section_number)
    compact = normalized.lower()
    compact = re.sub(r"[^a-z0-9-]", "", compact)
    compact = re.sub(r"-+", "-", compact).strip("-")
    return compact


def _candidate_file_names(section_number: str) -> list[str]:
    """Return candidate markdown filenames for a section number."""
    normalized = _normalize_section_number(section_number)
    if not normalized:
        return []

    compact = normalized.replace("-", "")
    candidates = [f"section-{normalized}.md"]
    if compact != normalized:
        candidates.append(f"section-{compact}.md")
    return candidates


def load_section_markdown(
    legal_acts_root: Path,
    act_code: str,
    section_number: str,
) -> tuple[bool, str | None, str | None]:
    """Load markdown source for a section.

    Returns:
        Tuple of (found, markdown_content, source_path_relative_to_legal_acts)
    """
    normalized_act = _normalize_act_code(act_code)
    if not _VALID_ACT_CODE.match(normalized_act):
        return (False, None, None)

    section_candidates = _candidate_file_names(section_number)
    if not section_candidates:
        return (False, None, None)

    if not _VALID_SECTION.match(_normalize_section_number(section_number)):
        return (False, None, None)

    markdown_dir = legal_acts_root / normalized_act / "markdown" / "sections"
    for filename in section_candidates:
        path = markdown_dir / filename
        if not path.exists() or not path.is_file():
            continue

        content = path.read_text(encoding="utf-8")
        relative_path = str(path.relative_to(legal_acts_root))
        return (True, content, relative_path)

    return (False, None, None)
