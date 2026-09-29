"""Streamlit UI for the HDFC MF Facts-Only RAG Chatbot."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure project root is on path when run as `streamlit run src/app/ui.py`
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.retrieve.orchestrator import answer_question
from src.retrieve.retriever import IndexMissingError

# --- Health check (for Render) --------------------------------------------------

if "health" in st.query_params:
    st.write("OK")
    st.stop()

# --- UI constants ---------------------------------------------------------------

DISCLAIMER = (
    "**Facts-only. No investment advice.** Answers are based on public scheme pages "
    "and may change. Verify on the official source before acting."
)

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
    "What is the lock-in period for HDFC ELSS Tax Saver?",
    "What is the exit load on HDFC Small Cap Fund Direct Growth?",
]

WELCOME = (
    "Welcome to the HDFC Mutual Fund Facts Assistant. "
    "Ask factual questions about HDFC Direct-Growth schemes — "
    "expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark, and more."
)

INGEST_CMD = "python -m src.ingest.run_ingest --reset"

# Conversation memory window (number of messages to keep)
# Kept small to ensure FAQ chunks stay within LLM context window
MEMORY_WINDOW = 4


# --- Streamlit app --------------------------------------------------------------

def _init_session() -> None:
    """Initialize session state for conversation memory."""
    if "memory" not in st.session_state:
        st.session_state["memory"] = []


def _add_to_memory(role: str, content: str) -> None:
    """Add a message to the rolling memory window."""
    memory = st.session_state["memory"]
    memory.append({"role": role, "content": content})
    # Keep only the last MEMORY_WINDOW messages
    if len(memory) > MEMORY_WINDOW:
        st.session_state["memory"] = memory[-MEMORY_WINDOW:]


def main() -> None:
    st.set_page_config(
        page_title="HDFC MF Facts Assistant",
        page_icon="📊",
        layout="centered",
    )

    _init_session()

    st.title("HDFC Mutual Fund Facts Assistant")
    st.markdown(WELCOME)

    # Always-visible disclaimer
    st.warning(DISCLAIMER)

    # Show conversation memory indicator
    memory = st.session_state.get("memory", [])
    if memory:
        st.caption(f"Memory: {len(memory)}/{MEMORY_WINDOW} messages in context")

    # Example questions
    st.subheader("Try an example:")
    cols = st.columns(len(EXAMPLE_QUESTIONS))
    for col, question in zip(cols, EXAMPLE_QUESTIONS):
        if col.button(question, use_container_width=True):
            st.session_state["pending_question"] = question

    # Chat input
    question = st.chat_input("Ask a factual question about HDFC schemes...")

    # If an example button was clicked, use that as the question
    if question is None and "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")

    if question:
        # Show user message
        with st.chat_message("user"):
            st.write(question)

        # Get and show assistant response
        with st.chat_message("assistant"):
            with st.spinner("Searching sources..."):
                try:
                    result = answer_question(question, history=memory)
                except IndexMissingError:
                    st.error(
                        f"Index not built yet. Run ingestion first:\n\n"
                        f"```\n{INGEST_CMD}\n```"
                    )
                    return
                except Exception as exc:
                    st.error(f"Something went wrong: {exc}")
                    return

            # Answer body
            st.write(result["answer"])

            # Citation footer
            if result.get("source"):
                st.markdown(f"**Source:** [{result['source']}]({result['source']})")
            if result.get("last_updated_from_sources"):
                st.caption(
                    f"Last updated from sources: {result['last_updated_from_sources']}"
                )

        # Update memory after successful exchange
        _add_to_memory("user", question)
        _add_to_memory("assistant", result["answer"])


if __name__ == "__main__":
    main()
