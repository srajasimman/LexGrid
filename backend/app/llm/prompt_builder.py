"""Prompt builder — system prompt, context formatter, user prompt."""

from __future__ import annotations

from app.models.chunk import LegalChunk

SYSTEM_PROMPT: str = (
    "You are a precise legal research assistant for Indian law. Follow these rules:\n"
    "1. Base your answer primarily on the legal text provided in the context.\n"
    "2. You may explain, synthesize, and paraphrase the law clearly — do not only quote verbatim.\n"
    "3. Every factual claim MUST be supported by a citation in the format [Section X, Act Name].\n"
    "4. If the context is partially relevant, answer what you can and state clearly what falls "
    "outside the provided text.\n"
    "5. Only respond with 'I cannot find this information in the provided legal texts.' if the "
    "context contains absolutely nothing related to the question.\n"
    "6. Never invent section numbers or facts not present in the context."
)


def build_system_prompt() -> str:
    """Return the immutable system-level instruction for the LLM."""
    return SYSTEM_PROMPT


def build_context(chunks: list[LegalChunk]) -> str:
    """Format retrieved chunks into a numbered context block.

    Each chunk is rendered as:
        [Section {number} — {act_name} ({act_year})]
        {content}
    """
    blocks = [
        f"[Section {c.section_number} — {c.act_name} ({c.act_year})]\n{c.content}" for c in chunks
    ]
    return "\n\n".join(blocks)


def build_user_prompt(query: str, context: str) -> str:
    """Combine the context block and the user's question into one message."""
    return f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer (cite all relevant sections):"
