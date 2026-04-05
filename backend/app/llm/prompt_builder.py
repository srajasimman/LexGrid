"""Prompt builder — system prompt, context formatter, user prompt."""

from __future__ import annotations

from app.models.chunk import LegalChunk

SYSTEM_PROMPT: str = (
    "You are a precise legal research assistant for Indian law. "
    "You MUST follow these rules:\n"
    "1. Answer ONLY using the legal text provided in the context below. "
    "Do NOT use any external knowledge.\n"
    "2. Every answer MUST include citations in the format [Section X, Act Name].\n"
    "3. If the answer cannot be found in the provided context, respond exactly: "
    '"I cannot find this information in the provided legal texts."\n'
    "4. Do not summarize or paraphrase law; quote the relevant text directly.\n"
    "5. Preserve legal precision — do not interpret beyond what is written."
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
