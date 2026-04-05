"""Chunker — converts raw section dicts into typed LegalChunk objects."""

from __future__ import annotations

import tiktoken

from app.models.chunk import ChunkType, LegalChunk

# Singleton encoder (loaded once per process)
_ENCODER = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Return approximate token count for *text* using cl100k_base encoding."""
    return len(_ENCODER.encode(text))


def _build_section_chunk(section: dict, idx: int) -> LegalChunk | None:
    """Create the primary SECTION chunk from the raw section dict.

    Returns None if the section has no text content (skipped silently).
    """
    act_code = section.get("act_code", "unknown")
    section_number = section.get("section_number", str(idx))
    content = section.get("text", "").strip()

    if not content:
        return None

    return LegalChunk(
        id=f"{act_code}-{section_number}-section",
        act_code=act_code,
        act_name=section.get("act_name", ""),
        act_year=str(section.get("act_year", "")),
        chapter_number=section.get("chapter_number"),
        chapter_title=section.get("chapter_title"),
        section_number=section_number,
        section_title=section.get("section_title"),
        content=content,
        chunk_type=ChunkType.SECTION,
        source_url=section.get("source_url"),
        token_count=count_tokens(content),
    )


def _build_explanation_chunks(section: dict) -> list[LegalChunk]:
    """Create one EXPLANATION chunk per non-empty explanation string."""
    act_code = section.get("act_code", "unknown")
    section_number = section.get("section_number", "?")
    explanations = section.get("explanations", [])
    chunks: list[LegalChunk] = []

    for idx, explanation in enumerate(explanations):
        text = explanation.strip() if isinstance(explanation, str) else ""
        if not text:
            continue
        content = f"Explanation to Section {section_number}: {text}"
        chunks.append(
            LegalChunk(
                id=f"{act_code}-{section_number}-explanation-{idx}",
                act_code=act_code,
                act_name=section.get("act_name", ""),
                act_year=str(section.get("act_year", "")),
                chapter_number=section.get("chapter_number"),
                chapter_title=section.get("chapter_title"),
                section_number=section_number,
                section_title=section.get("section_title"),
                content=content,
                chunk_type=ChunkType.EXPLANATION,
                source_url=section.get("source_url"),
                token_count=count_tokens(content),
            )
        )
    return chunks


def chunk_section(section: dict) -> list[LegalChunk]:
    """Convert one raw section dict to a list of LegalChunk objects.

    Returns an empty list if the section has no text content.
    Additional EXPLANATION chunks are appended when non-empty explanations exist.

    Args:
        section: Raw dict loaded from legal-acts/{act}/json/sections/*.json

    Returns:
        List of LegalChunk; first entry (if present) is ChunkType.SECTION.
        May be empty if the section text is blank.
    """
    primary = _build_section_chunk(section, idx=0)
    if primary is None:
        return []
    explanations = _build_explanation_chunks(section)
    return [primary, *explanations]
