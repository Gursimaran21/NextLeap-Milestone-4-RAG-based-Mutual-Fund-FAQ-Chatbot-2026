"""Embed + Store stage: Google Gemini embeddings persisted in ChromaDB."""

from __future__ import annotations

import os
import time
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai._common import GoogleGenerativeAIError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL

# Rate limit handling
BATCH_SIZE = 20
DELAY_SECONDS = 6


@lru_cache(maxsize=1)
def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    """Load (and cache) the Google Gemini embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )


@retry(
    retry=retry_if_exception_type((GoogleGenerativeAIError, Exception)),
    wait=wait_exponential(multiplier=2, min=10, max=60),
    stop=stop_after_attempt(5),
)
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
    """
    Embed a list of texts with Google Gemini in batches.

    Processes texts in batches with a delay between each batch to respect
    the Gemini API free-tier rate limit (100 requests/minute).
    """
    encoder = model or get_embedding_model()
    all_embeddings: list[list[float]] = []

    total = len(texts)
    num_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, total, BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"  Embedding batch {batch_num}/{num_batches} ({len(batch)} chunks)...")

        batch_embeddings = safe_embed_documents(encoder, batch)
        all_embeddings.extend(batch_embeddings)

        # Pause between batches to stay within rate limits
        if i + BATCH_SIZE < total:
            time.sleep(DELAY_SECONDS)

    return all_embeddings


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

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        ids = [chunk["id"] for chunk in batch]
        documents = [chunk["text"] for chunk in batch]
        metadatas = [_chroma_metadata(chunk) for chunk in batch]

        embeddings = embed_texts(documents, model=model)

        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

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
