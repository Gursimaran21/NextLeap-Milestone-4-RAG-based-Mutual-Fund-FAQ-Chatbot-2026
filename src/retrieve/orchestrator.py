"""Orchestrator: wire guardrails -> retrieve -> generate."""

from __future__ import annotations

import re
from typing import Any

from src.retrieve.generate import generate_answer
from src.retrieve.guardrails import check_question
from src.retrieve.retriever import IndexMissingError, retrieve

# Known scheme names for optional metadata filter
KNOWN_SCHEMES = [
    "HDFC Large Cap Fund Direct Growth",
    "HDFC Equity Fund Direct Growth",
    "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "HDFC Small Cap Fund Direct Growth",
    "HDFC Balanced Advantage Fund Direct Growth",
]


def _extract_scheme(question: str) -> str | None:
    """Naive scheme name extraction from question text."""
    q_lower = question.lower()
    for scheme in KNOWN_SCHEMES:
        # Match on distinctive parts of the scheme name
        key = scheme.lower().replace(" direct growth", "").replace(" direct plan growth", "")
        if key in q_lower:
            return scheme
    return None


def _build_query_with_history(
    question: str, history: list[dict[str, str]]
) -> str:
    """
    Enrich the question with conversation context for better retrieval.

    If the question seems like a follow-up (short, no scheme name),
    prepend relevant history so the retriever can find the right chunks.
    """
    if not history:
        return question

    # If question already names a scheme, no need for history
    if _extract_scheme(question):
        return question

    # Build a context string from recent history
    context_parts: list[str] = []
    for msg in history[-6:]:  # last 6 messages (3 turns)
        role = msg.get("role", "")
        content = msg.get("content", "").strip()
        if content:
            context_parts.append(f"{role}: {content}")

    if not context_parts:
        return question

    context_str = " | ".join(context_parts)
    return f"[Conversation context: {context_str}] Current question: {question}"


def answer_question(
    question: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Full runtime path: guardrails -> retrieve -> generate.

    Args:
        question: The user's current question.
        history: Optional list of prior messages (role/content dicts)
                 for conversational context.

    Returns:
      Fact: {answer, source, last_updated_from_sources, refused: False}
      Refusal: {answer, source: None, last_updated_from_sources: None, refused: True}
    """
    # 1. Guardrails
    guard = check_question(question)
    if not guard["ok"]:
        return {
            "answer": guard["refusal_message"],
            "source": None,
            "last_updated_from_sources": None,
            "refused": True,
        }

    # 2. Optional scheme filter
    scheme = _extract_scheme(question)

    # 3. Enrich query with conversation history for better retrieval
    enriched_query = _build_query_with_history(question, history or [])

    # 4. Retrieve
    try:
        chunks = retrieve(enriched_query, scheme_name=scheme)
    except IndexMissingError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Retrieval failed: {exc}") from exc

    # 5. Generate (pass original question so the answer is natural)
    result = generate_answer(question, chunks)
    return result


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    demos = [
        "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
        "Should I buy HDFC Small Cap?",
        "What is the lock-in period for HDFC ELSS Tax Saver?",
    ]

    for q in demos:
        print(f"\nQ: {q}")
        try:
            result = answer_question(q)
        except Exception as exc:
            print(f"  ERROR: {exc}")
            continue
        if result["refused"]:
            print(f"  REFUSED: {result['answer'][:120]}...")
        else:
            print(f"  A: {result['answer']}")
            print(f"  Source: {result['source']}")
            print(f"  Last updated: {result['last_updated_from_sources']}")
