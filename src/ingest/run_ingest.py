"""CLI entry: run the full ingestion pipeline (Load -> Chunk -> Embed -> Store)."""

from __future__ import annotations

import argparse
import sys
import os
from langchain_community.vectorstores import Chroma  # or FAISS / Qdrant / Pinecone
from langchain_openai import OpenAIEmbeddings

# Initialize OpenAI Embeddings (Lightweight RAM usage, uses API)
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Example usage when creating/loading your vector store:
# vectorstore = Chroma.from_documents(documents, embeddings, persist_directory="./chroma_db")

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

    from src.ingest.chunk import chunk_documents
    from src.ingest.embed_store import embed_and_store
    from src.ingest.load import load_documents

    print("Loading documents...")
    docs = load_documents()
    print(f"  {len(docs)} documents loaded")

    print("Chunking...")
    chunks = chunk_documents(docs)
    print(f"  {len(chunks)} chunks created")

    print("Embedding + storing...")
    count = embed_and_store(chunks, reset=args.reset)
    print(f"  Stored {count} vectors")
    print("Done.")


if __name__ == "__main__":
    main()
