"""Export chunks + embeddings as readable .txt files under data/."""

from __future__ import annotations

from src.config import CHUNKS_DIR, EMBEDDING_MODEL, EMBEDDINGS_DIR
from src.ingest.chunk import chunk_documents
from src.ingest.embed_store import embed_texts, get_collection, get_embedding_model
from src.ingest.export_artifacts import export_chunks, export_embeddings_txt, export_raw_documents
from src.ingest.load import load_documents


def _records_from_chroma() -> list[dict]:
    """Pull stored documents + embeddings from Chroma."""
    collection = get_collection()
    count = collection.count()
    if count == 0:
        raise RuntimeError("Chroma collection is empty. Run embed_store / ingest first.")

    result = collection.get(include=["documents", "metadatas", "embeddings"])
    ids = result.get("ids") or []
    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []
    embeddings = result.get("embeddings")
    if embeddings is None:
        raise RuntimeError("Chroma did not return embeddings.")

    records: list[dict] = []
    for i, chunk_id in enumerate(ids):
        meta = metadatas[i] or {}
        records.append(
            {
                "id": chunk_id,
                "text": documents[i] or "",
                "scheme_name": meta.get("scheme_name", ""),
                "category": meta.get("category", ""),
                "chunk_index": meta.get("chunk_index", i),
                "source_url": meta.get("source_url", ""),
                "ingested_at": meta.get("ingested_at", ""),
                "embedding": list(embeddings[i]),
            }
        )
    # Stable order for reading
    records.sort(key=lambda r: (str(r["scheme_name"]), int(r["chunk_index"])))
    return records


def _records_from_reembed(chunks: list[dict]) -> list[dict]:
    """Fallback: re-embed chunks if Chroma has no vectors yet."""
    model = get_embedding_model()
    vectors = embed_texts([c["text"] for c in chunks], model=model)
    records = []
    for chunk, emb in zip(chunks, vectors):
        records.append({**chunk, "embedding": emb})
    return records


def main() -> None:
    print("Load…")
    docs = load_documents()
    export_raw_documents(docs)
    print(f"  raw txt -> data/raw/ ({len(docs)} files)")

    print("Chunk…")
    chunks = chunk_documents(docs)
    chunks_txt = export_chunks(chunks)
    print(f"  chunks txt -> {chunks_txt}")
    print(f"  also per-scheme txt under {CHUNKS_DIR}")

    print("Embeddings…")
    try:
        records = _records_from_chroma()
        print(f"  loaded {len(records)} vectors from Chroma")
    except Exception as exc:
        print(f"  Chroma read failed ({exc}); re-embedding chunks…")
        records = _records_from_reembed(chunks)

    emb_path = export_embeddings_txt(records, model_name=EMBEDDING_MODEL)
    print(f"  embeddings txt -> {emb_path}")
    print(f"  also index + per-scheme under {EMBEDDINGS_DIR}")
    print("Done.")


if __name__ == "__main__":
    main()
