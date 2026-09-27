"""Embed + Store stage: OpenAI embeddings persisted in ChromaDB."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from src.config import CHROMA_COLLECTION, CHROMA_PATH, EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embedding_model() -> OpenAIEmbeddings:
    """Load (and cache) the OpenAI embeddings model."""
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=os.getenv("GEMINI_API_KEY")
)


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
    model: OpenAIEmbeddings | None = None,
) -> list[list[float]]:
    """Embed a list of texts with OpenAI; returns list of vectors."""
    encoder = model or get_embedding_model()
    return encoder.embed_documents(texts)


def embed_and_store(
    chunks: list[dict[str, Any]],
    *,
    reset: bool = False,
    batch_size: int = 64,
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
