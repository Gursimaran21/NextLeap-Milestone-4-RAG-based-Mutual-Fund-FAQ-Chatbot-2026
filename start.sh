#!/usr/bin/env bash
set -e

echo "Running ingestion..."
python -m src.ingest.run_ingest --reset

echo "Starting Streamlit..."
exec streamlit run src/app/ui.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
