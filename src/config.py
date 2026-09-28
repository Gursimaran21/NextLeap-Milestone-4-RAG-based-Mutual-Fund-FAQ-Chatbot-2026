"""Shared configuration for the HDFC MF facts-only RAG chatbot."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
RAW_DIR = DATA_DIR / "raw"
CHUNKS_DIR = DATA_DIR / "chunks"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"
SOURCES_CSV = DATA_DIR / "sources.csv"
CHROMA_PATH = PROJECT_ROOT / "chroma"

# Chunking (architecture §10)
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

# Retrieval
TOP_K = 4

# Embeddings (Google Gemini)
EMBEDDING_MODEL = "gemini-embedding-001"

# Vector store
CHROMA_COLLECTION = "hdfc_mf_faqs"

# LLM (Google Gemini via OpenAI-compatible endpoint)
LLM_API_KEY_ENV = "GEMINI_API_KEY"
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.0-flash")
LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Gemini embeddings API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
