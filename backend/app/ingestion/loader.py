"""Loader — reads raw JSON files from the legal-acts/ directory."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import get_settings


def _legal_acts_dir() -> Path:
    """Return the resolved legal-acts directory from settings."""
    return get_settings().legal_acts_path


def list_available_acts() -> list[str]:
    """Return sorted list of act_code directories found in legal-acts/."""
    legal_acts_dir = _legal_acts_dir()
    if not legal_acts_dir.exists():
        raise FileNotFoundError(f"legal-acts directory not found: {legal_acts_dir}")
    return sorted(
        p.name for p in legal_acts_dir.iterdir() if p.is_dir() and not p.name.startswith(".")
    )


def load_act_sections(act_code: str) -> list[dict]:
    """Read all section JSON files for the given act_code.

    Args:
        act_code: Short act identifier, e.g. 'ipc', 'crpc'.

    Returns:
        List of raw section dicts, one per JSON file.

    Raises:
        FileNotFoundError: If the sections directory does not exist.
    """
    sections_dir = _legal_acts_dir() / act_code / "json" / "sections"
    if not sections_dir.exists():
        raise FileNotFoundError(
            f"Sections directory not found for act '{act_code}': {sections_dir}"
        )

    sections: list[dict] = []
    for path in sorted(sections_dir.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
            # Ensure act_code is present (some files may omit it)
            data.setdefault("act_code", act_code)
            sections.append(data)

    return sections
