"""Retrieve stage: embed query and similarity-search ChromaDB."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL, TOP_K


class IndexMissingError(RuntimeError):
    """Raised when the Chroma collection is missing or empty."""


@lru_cache(maxsize=1)
def _get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    """Load (and cache) the Google Gemini embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


def _get_query_collection():
    """Open the existing FAQ collection; fail clearly if missing/empty."""
    if not CHROMA_PATH.exists():
        raise IndexMissingError(
            f"Chroma path not found: {CHROMA_PATH}. "
            "Run ingestion first (e.g. python -m src.ingest.run_ingest)."
        )

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    names = {c.name for c in client.list_collections()}
    if CHROMA_COLLECTION not in names:
        raise IndexMissingError(
            f"Collection '{CHROMA_COLLECTION}' not found in {CHROMA_PATH}. "
            "Run ingestion first."
        )

    collection = client.get_collection(CHROMA_COLLECTION)
    if collection.count() == 0:
        raise IndexMissingError(
            f"Collection '{CHROMA_COLLECTION}' is empty. "
            "Run ingestion first."
        )
    return collection


def retrieve(
    question: str,
    top_k: int | None = None,
    scheme_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Embed the question and return top-k similar chunks from Chroma.

    Each result:
      {
        id, text, metadata, distance, score,
        source_url, scheme_name, category, ingested_at, chunk_index
      }
    """
    text = (question or "").strip()
    if not text:
        raise ValueError("question must be a non-empty string")

    k = top_k if top_k is not None else TOP_K
    if k < 1:
        raise ValueError("top_k must be >= 1")

    collection = _get_query_collection()
    model = _get_embedding_model()
    query_embedding = model.embed_query(text)

    query_kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": k,
        "include": ["documents", "metadatas", "distances"],
    }
    if scheme_name:
        query_kwargs["where"] = {"scheme_name": scheme_name}

    result = collection.query(**query_kwargs)

    ids = (result.get("ids") or [[]])[0]
    documents = (result.get("documents") or [[]])[0]
    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    hits: list[dict[str, Any]] = []
    for i, chunk_id in enumerate(ids):
        meta = dict(metadatas[i] or {})
        distance = float(distances[i]) if distances is not None else None
        # Cosine space in Chroma: distance lower is better; map to [0, 1]-ish score
        score = (1.0 - distance) if distance is not None else None
        hits.append(
            {
                "id": chunk_id,
                "text": documents[i] or "",
                "metadata": meta,
                "distance": distance,
                "score": score,
                "source_url": meta.get("source_url", ""),
                "scheme_name": meta.get("scheme_name", ""),
                "category": meta.get("category", ""),
                "ingested_at": meta.get("ingested_at", ""),
                "chunk_index": meta.get("chunk_index"),
            }
        )
    return hits


if __name__ == "__main__":
    import sys

    # Avoid Windows cp1252 crashes on ₹ / other unicode in page text
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    demos = [
        ("expense ratio large cap", None),
        (
            "What is the expense ratio of HDFC Large Cap Fund?",
            "HDFC Large Cap Fund Direct Growth",
        ),
    ]

    for query, scheme in demos:
        label = f"Query: {query!r}"
        if scheme:
            label += f"  [filter scheme_name={scheme!r}]"
        print(label + "\n")
        try:
            hits = retrieve(query, scheme_name=scheme)
        except IndexMissingError as exc:
            print(f"ERROR: {exc}")
            raise SystemExit(1) from exc

        for i, hit in enumerate(hits, start=1):
            preview = hit["text"].replace("\n", " ")
            if len(preview) > 220:
                preview = preview[:220] + "..."
            print(f"--- hit {i} ---")
            print(f"scheme:   {hit['scheme_name']}")
            print(f"score:    {hit['score']:.4f}  (distance={hit['distance']:.4f})")
            print(f"source:   {hit['source_url']}")
            print(f"preview:  {preview}")
            print()
        print("=" * 72 + "\n")
