#!/usr/bin/env bash
set -e

# Set root directory in PYTHONPATH
export PYTHONPATH=.

echo "Running ingestion..."
python -m src.ingest.run_ingest --reset

echo "Starting Streamlit..."
exec streamlit run src/app/ui.py --server.port $PORT --server.address 0.0.0.0 --server.headless true

# Launch application (Example for Streamlit)
streamlit run app.py --server.port $PORT --server.address 0.0.0.0