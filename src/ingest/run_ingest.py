"""CLI entry: run the full ingestion pipeline (Load -> Chunk -> Embed -> Store)."""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full ingestion pipeline.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the Chroma collection before ingesting.",
    )
    args = parser.parse_args()

    # Avoid Windows cp1252 crashes on unicode
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import csv
    from pathlib import Path

    from src.ingest.chunk import chunk_documents
    from src.ingest.embed_store import embed_and_store
    from src.ingest.load import load_documents

    print("Loading documents...")
    docs = load_documents()
    print(f"  {len(docs)} documents loaded")

    print("Chunking...")
    chunks = chunk_documents(docs)
    print(f"  {len(chunks)} chunks created")

    # Load FAQ entries as additional chunks
    faq_path = Path(__file__).resolve().parent.parent.parent / "data" / "faq.csv"
    if faq_path.exists():
        with faq_path.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                faq_text = f"Q: {row['question']}\nA: {row['answer']}"
                chunks.append(
                    {
                        "id": f"faq_{row['id']}",
                        "text": faq_text,
                        "source_url": "https://www.hdfcfund.com",
                        "scheme_name": "General FAQ",
                        "category": row["category"],
                        "ingested_at": "2026-09-29T00:00:00+00:00",
                        "chunk_index": f"faq_{i}",
                    }
                )
        print(f"  {len(chunks)} total chunks (including FAQ)")

    print("Embedding + storing...")
    count = embed_and_store(chunks, reset=args.reset)
    print(f"  Stored {count} vectors")
    print("Done.")


if __name__ == "__main__":
    main()
