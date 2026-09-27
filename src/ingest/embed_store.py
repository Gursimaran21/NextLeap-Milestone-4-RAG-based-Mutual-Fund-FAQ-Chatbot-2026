"""Embed + Store stage: Google Gemini embeddings persisted in ChromaDB."""

from __future__ import annotations

import os
import time
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL

# Rate limit handling
BATCH_SIZE = 20
DELAY_SECONDS = 2


@lru_cache(maxsize=1)
def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    """Load (and cache) the Google Gemini embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        batch_size=BATCH_SIZE,
    )


@retry(wait=wait_exponential(multiplier=1, min=5, max=60), stop=stop_after_attempt(5))
def safe_embed_documents(encoder: GoogleGenerativeAIEmbeddings, texts: list[str]) -> list[list[float]]:
    """Embed documents with automatic retry on rate limit (429) errors."""
    return encoder.embed_documents(texts)


def get_chroma_client(path: str | None = None) -> chromadb.PersistentClient:
    """Return a persistent Chroma client under chroma/."""
    chroma_path = path or str(CHROMA_PATH)
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=chroma_path)


def get_collection(
    *,
    reset: bool = False,
    client: chromadb.PersistentClient | None = None,
) -> Collection:
    """Get or create the FAQ collection; optionally delete first."""
    chroma = client or get_chroma_client()
    if reset:
        try:
            chroma.delete_collection(CHROMA_COLLECTION)
        except Exception:
            # Collection may not exist yet
            pass
    return chroma.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection(
    client: chromadb.PersistentClient | None = None,
) -> Collection:
    """Drop and recreate the Chroma collection (clean re-ingest)."""
    return get_collection(reset=True, client=client)


def collection_count(
    collection: Collection | None = None,
) -> int:
    """Return number of vectors currently stored."""
    coll = collection or get_collection()
    return coll.count()


def _chroma_metadata(chunk: dict[str, Any]) -> dict[str, str | int]:
    """Chroma-safe metadata (str/int/float/bool only)."""
    return {
        "source_url": str(chunk["source_url"]),
        "scheme_name": str(chunk["scheme_name"]),
        "category": str(chunk["category"]),
        "ingested_at": str(chunk["ingested_at"]),
        "chunk_index": int(chunk["chunk_index"]),
    }


def embed_texts(
    texts: list[str],
    *,
    model: GoogleGenerativeAIEmbeddings | None = None,
) -> list[list[float]]:
    """Embed a list of texts with Google Gemini; returns list of vectors."""
    encoder = model or get_embedding_model()
    return safe_embed_documents(encoder, texts)


def embed_and_store(
    chunks: list[dict[str, Any]],
    *,
    reset: bool = False,
    batch_size: int = BATCH_SIZE,
) -> int:
    """
    Embed chunks and upsert into ChromaDB.

    Returns the collection count after upsert.
    """
    if not chunks:
        raise ValueError("No chunks to embed and store.")

    collection = get_collection(reset=reset)
    model = get_embedding_model()

    total = len(chunks)
    for start in range(0, total, batch_size):
        batch = chunks[start : start + batch_size]
        ids = [chunk["id"] for chunk in batch]
        documents = [chunk["text"] for chunk in batch]
        metadatas = [_chroma_metadata(chunk) for chunk in batch]

        print(f"  Embedding batch {start // batch_size + 1}/{(total - 1) // batch_size + 1} ({len(batch)} chunks)...")
        embeddings = embed_texts(documents, model=model)

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        # Pause between batches to respect rate limits
        if start + batch_size < total:
            time.sleep(DELAY_SECONDS)

    return collection_count(collection)


if __name__ == "__main__":
    from src.ingest.chunk import chunk_documents
    from src.ingest.load import load_documents

    print("Load…")
    docs = load_documents()
    print(f"  {len(docs)} documents")

    print("Chunk…")
    chunks = chunk_documents(docs)
    print(f"  {len(chunks)} chunks")

    print("Embed + Store…")
    count = embed_and_store(chunks, reset=True)
    print(f"  Stored {count} vectors in collection '{CHROMA_COLLECTION}'")
    print(f"  Path: {CHROMA_PATH}")
