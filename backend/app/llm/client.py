"""LLM client — calls gpt-4o-mini and extracts legal citations from response."""

from __future__ import annotations

import re

from openai import AsyncOpenAI

from app.config import Settings
from app.llm.prompt_builder import build_context, build_system_prompt, build_user_prompt
from app.models.chunk import LegalChunk
from app.models.query import Citation

# Matches patterns like [Section 302, Indian Penal Code]
_CITATION_RE = re.compile(
    r"\[Section\s+([\dA-Za-z]+)\s*,\s*([^\]]+)\]",
    re.IGNORECASE,
)


def _parse_citations(
    text: str,
    chunks: list[LegalChunk],
) -> list[Citation]:
    """Extract Citation objects from LLM answer text."""
    citations: list[Citation] = []
    for match in _CITATION_RE.finditer(text):
        section_num, act_name_raw = match.group(1), match.group(2).strip()
        # Find matching chunk to populate act_code + source_url
        matched = next((c for c in chunks if c.section_number == section_num), None)
        citations.append(
            Citation(
                act_code=matched.act_code if matched else "unknown",
                act_name=act_name_raw,
                section_number=section_num,
                section_title=matched.section_title if matched else None,
                source_url=matched.source_url if matched else None,
            )
        )
    return citations


async def stream_answer(
    query: str,
    chunks: list[LegalChunk],
    settings: Settings,
):
    """Stream LLM tokens as an async generator, then yield parsed citations.

    Yields dicts:
        {"type": "token", "content": "<text>"}   — one per streamed chunk
        {"type": "citations", "citations": [...]} — after stream ends
        {"type": "done"}                          — terminal event
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(query, context)},
    ]
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        messages=messages,
        max_tokens=settings.llm_max_tokens,
        stream=True,
    )
    full_answer: list[str] = []
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            full_answer.append(delta)
            yield {"type": "token", "content": delta}

    answer = "".join(full_answer)
    citations = _parse_citations(answer, chunks)
    yield {"type": "citations", "citations": [c.model_dump() for c in citations]}

    # Generate a short session title from the Q&A
    try:
        title_response = await client.chat.completions.create(
            model=settings.llm_model,
            temperature=0.3,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Generate a concise 4-6 word title for this legal Q&A session. "
                        "Reply with only the title, no punctuation, no quotes.\n\n"
                        f"Question: {query}\n"
                        f"Answer summary: {answer[:300]}"
                    ),
                }
            ],
            max_tokens=20,
        )
        title = (title_response.choices[0].message.content or "").strip()
    except Exception:
        title = query[:60]

    yield {"type": "title", "title": title}
    yield {"type": "done"}


async def generate_answer(
    query: str,
    chunks: list[LegalChunk],
    settings: Settings,
) -> tuple[str, list[Citation]]:
    """Call the LLM and return (answer, citations).

    Args:
        query: User's legal question.
        chunks: Retrieved chunks used as grounding context.
        settings: App settings (model, temperature, API key).

    Returns:
        Tuple of the generated answer string and parsed Citation objects.
    """
    client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": build_user_prompt(query, context)},
    ]
    response = await client.chat.completions.create(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        messages=messages,
        max_tokens=1024,
    )
    answer: str = response.choices[0].message.content or ""
    citations = _parse_citations(answer, chunks)
    return answer, citations
