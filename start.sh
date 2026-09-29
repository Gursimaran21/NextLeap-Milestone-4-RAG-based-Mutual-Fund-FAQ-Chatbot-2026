#!/usr/bin/env bash
set -e

# Set root directory in PYTHONPATH
export PYTHONPATH=.

# Only run ingestion if the Chroma vector store doesn't exist
# (pre-built chroma/ directory is committed to the repo)
if [ ! -d "chroma" ] || [ -z "$(ls -A chroma 2>/dev/null)" ]; then
  echo "Chroma vector store not found. Running ingestion..."
  python -m src.ingest.run_ingest --reset
else
  echo "Chroma vector store found. Skipping ingestion."
fi

# Warm up: load embedding model and verify vector store
# This prevents cold-start failures on Render free tier
echo "Warming up embedding model..."
python warmup.py

echo "Starting Streamlit..."
exec streamlit run src/app/ui.py --server.port $PORT --server.address 0.0.0.0 --server.headless true