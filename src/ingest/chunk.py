"""Chunk stage: recursive character splitting of loaded documents."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import CHUNK_OVERLAP, CHUNK_SIZE
from src.ingest.export_artifacts import export_chunks, export_raw_documents
from src.ingest.load import load_documents


def _chunk_id(scheme_name: str, chunk_index: int) -> str:
    raw = f"{scheme_name}::{chunk_index}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def chunk_documents(
    documents: list[dict[str, Any]] | None = None,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[dict[str, Any]]:
    """
    Split documents into retrieval chunks.

    Each chunk: {id, text, source_url, scheme_name, category, ingested_at, chunk_index}
    """
    docs = documents if documents is not None else load_documents()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size if chunk_size is not None else CHUNK_SIZE,
        chunk_overlap=chunk_overlap if chunk_overlap is not None else CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        is_separator_regex=False,
    )

    chunks: list[dict[str, Any]] = []
    for doc in docs:
        pieces = splitter.split_text(doc["text"])
        for index, piece in enumerate(pieces):
            text = piece.strip()
            if not text:
                continue
            chunks.append(
                {
                    "id": _chunk_id(doc["scheme_name"], index),
                    "text": text,
                    "source_url": doc["source_url"],
                    "scheme_name": doc["scheme_name"],
                    "category": doc["category"],
                    "ingested_at": doc["ingested_at"],
                    "chunk_index": index,
                }
            )

    return chunks


if __name__ == "__main__":
    docs = load_documents()
    export_raw_documents(docs)
    chunks = chunk_documents(docs)
    out = export_chunks(chunks)

    per_scheme: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        per_scheme[chunk["scheme_name"]] += 1

    print(f"Documents: {len(docs)}")
    print(f"Total chunks: {len(chunks)}\n")
    for scheme, count in per_scheme.items():
        print(f"{scheme}: {count} chunks")
    print(f"\nRaw text -> data/raw/")
    print(f"Chunks   -> {out}")
