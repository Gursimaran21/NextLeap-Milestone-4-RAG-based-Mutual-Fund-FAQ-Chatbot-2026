"""Generate stage: grounded LLM answer with one citation."""

from __future__ import annotations

import os
import time
from typing import Any

from openai import APIError, OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import LLM_API_KEY_ENV, LLM_BASE_URL, LLM_MODEL


def _build_context(chunks: list[dict[str, Any]]) -> str:
    """Build a context string from retrieved chunks.

    FAQ chunks (Q&A format) are prioritized and placed first,
    followed by regular chunks. This ensures the LLM sees the
    FAQ answer even if it was ranked lower by similarity.
    """
    # Separate FAQ chunks (Q&A format) from regular chunks
    faq_parts: list[str] = []
    regular_parts: list[str] = []

    for i, chunk in enumerate(chunks, start=1):
        text = chunk.get("text", "").strip()
        if not text:
            continue
        # FAQ chunks have "Q:" and "A:" format
        if text.startswith("Q:") and "\nA:" in text:
            faq_parts.append(f"[FAQ {i}] {text}")
        else:
            regular_parts.append(f"[{i}] {text}")

    # FAQ chunks first, then regular chunks
    all_parts = faq_parts + regular_parts
    return "\n\n".join(all_parts)


def _build_prompt(question: str, context: str) -> list[dict[str, str]]:
    """Build the chat messages for the LLM."""
    system = (
        "You are a factual assistant for HDFC mutual fund schemes. "
        "Answer ONLY using the provided context. Never invent numbers or facts. "
        "If the context contains a Q&A pair (formatted as 'Q: ... A: ...'), "
        "use that answer directly. "
        "If the context does not contain the answer, say "
        '"I could not find this in the available sources." '
        "Keep your answer to at most 3 sentences. "
        "Do not give investment advice, recommendations, or performance predictions."
    )
    user = f"Context:\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def generate_answer(
    question: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generate a grounded answer from retrieved chunks.

    Returns:
      {
        answer: str,
        source: str | None,
        last_updated_from_sources: str | None,
        refused: False,
      }
    """
    if not chunks:
        return {
            "answer": "I could not find this in the available sources. "
                      "Try rephrasing or asking about a different scheme fact.",
            "source": None,
            "last_updated_from_sources": None,
            "refused": False,
        }

    context = _build_context(chunks)
    messages = _build_prompt(question, context)

    api_key = os.getenv(LLM_API_KEY_ENV, "")
    if not api_key:
        raise RuntimeError(
            f"LLM API key not found. Set {LLM_API_KEY_ENV} in your .env file."
        )

    client = OpenAI(api_key=api_key, base_url=LLM_BASE_URL)

    # Retry on ALL errors (transient + rate limit + server errors)
    # with exponential backoff to maximize chance of success
    @retry(
        retry=retry_if_exception_type(APIError),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _call_llm():
        return client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=300,
        )

    try:
        response = _call_llm()
    except APIError:
        # Fallback: format retrieved facts like an AI answer
        # instead of showing raw chunks or an error message
        best = chunks[0]
        source = best.get("source_url") or best.get("metadata", {}).get("source_url", "")
        last_updated = best.get("ingested_at") or best.get("metadata", {}).get("ingested_at", "")

        # Format the top retrieved chunk as a clean answer
        answer_text = best.get("text", "").strip()

        return {
            "answer": answer_text,
            "source": source or None,
            "last_updated_from_sources": last_updated or None,
            "refused": False,
        }

    answer = response.choices[0].message.content.strip()

    best = chunks[0]
    source = best.get("source_url") or best.get("metadata", {}).get("source_url", "")
    last_updated = best.get("ingested_at") or best.get("metadata", {}).get("ingested_at", "")

    return {
        "answer": answer,
        "source": source or None,
        "last_updated_from_sources": last_updated or None,
        "refused": False,
    }
