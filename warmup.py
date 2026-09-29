"""Warmup script: initialize embedding model and verify vector store.

Run this before starting Streamlit to avoid cold-start failures on Render.
"""

from __future__ import annotations

import sys
import time


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("Warming up embedding model...")
    start = time.time()

    try:
        from src.retrieve.retriever import _get_embedding_model, _get_query_collection

        # Load the embedding model (downloads on first run)
        model = _get_embedding_model()
        print(f"  Embedding model loaded in {time.time() - start:.1f}s")

        # Verify the vector store is accessible
        collection = _get_query_collection()
        count = collection.count()
        print(f"  Vector store verified: {count} vectors")

        # Run a test query to ensure end-to-end works
        test_embedding = model.embed_query("test")
        print(f"  Test embedding generated ({len(test_embedding)} dims)")

        print(f"Warmup complete in {time.time() - start:.1f}s")
        return 0

    except Exception as exc:
        print(f"Warmup failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
