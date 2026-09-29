"""Embed + Store stage: Google Gemini embeddings persisted in ChromaDB."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from src.config import CHROMA_COLLECTION, CHROMA_PATH

# Local embeddings — no rate limits needed
BATCH_SIZE = 20


@lru_cache(maxsize=1)
def get_embedding_model():
    """Load (and cache) ChromaDB's ONNX MiniLM embedding function (lightweight)."""
    return embedding_functions.DefaultEmbeddingFunction()


def safe_embed_documents(encoder, texts: list[str]) -> list[list[float]]:
    """Embed documents using the local model (no API rate limits)."""
    return encoder(texts)


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
    chunk_index = chunk["chunk_index"]
    # Fact chunks use string indices like "fact_0", regular chunks use ints
    if isinstance(chunk_index, int):
        idx_value: str | int = chunk_index
    else:
        idx_value = str(chunk_index)
    return {
        "source_url": str(chunk["source_url"]),
        "scheme_name": str(chunk["scheme_name"]),
        "category": str(chunk["category"]),
        "ingested_at": str(chunk["ingested_at"]),
        "chunk_index": idx_value,
    }


def embed_texts(
    texts: list[str],
    *,
    model=None,
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

        # No delay needed — local embeddings have no rate limits

    return all_embeddings


def embed_and_store(
    chunks: list[dict[str, Any]],
    *,
    reset: bool = False,
    batch_size: int = BATCH_SIZE,
) -> int:
    """
    Embed chunks and upsert into ChromaDB.

    Processes in batches with delays to respect Gemini free-tier rate limits.
    Uses checkpointing: already-embedded chunk IDs are skipped on re-runs.

    Returns the collection count after upsert.
    """
    if not chunks:
        raise ValueError("No chunks to embed and store.")

    collection = get_collection(reset=reset)
    model = get_embedding_model()

    # Determine which chunks are already stored (for resume support)
    existing_ids: set[str] = set()
    try:
        existing_ids = set(collection.get(ids=None, include=[])["ids"])
    except Exception:
        pass

    total = len(chunks)
    num_batches = (total + batch_size - 1) // batch_size

    for i in range(0, total, batch_size):
        batch = chunks[i : i + batch_size]
        batch_num = i // batch_size + 1

        # Skip batches where all chunks are already stored
        batch_ids = [chunk["id"] for chunk in batch]
        if all(cid in existing_ids for cid in batch_ids):
            print(f"  Batch {batch_num}/{num_batches} already stored, skipping...")
            continue

        documents = [chunk["text"] for chunk in batch]
        metadatas = [_chroma_metadata(chunk) for chunk in batch]

        print(f"  Embedding batch {batch_num}/{num_batches} ({len(batch)} chunks)...")
        embeddings = safe_embed_documents(model, documents)

        collection.upsert(
            ids=batch_ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        # No delay needed — local embeddings have no rate limits

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
