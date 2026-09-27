# HDFC Mutual Fund FAQ Chatbot

A **facts-only RAG chatbot** that answers factual questions about HDFC mutual fund schemes using a fixed corpus of 5 public Groww pages. Every answer cites one source URL. Investment advice and performance predictions are refused.

## Features

- **Retrieval-Augmented Generation (RAG)** pipeline with visible stages
- **Facts-only answers** (max 3 sentences) with one citation per response
- **Guardrails** that refuse advice, performance comparisons, and PII
- **Conversational memory** (last 10 messages) for follow-up questions
- **Streamlit UI** with welcome message, disclaimer, and 3 example questions
- **ChromaDB** local vector store with MiniLM embeddings

## Tech Stack

| Layer | Technology |
|-------|------------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | ChromaDB |
| LLM | OpenAI-compatible API (default: `gpt-4o-mini`) |
| UI | Streamlit |
| Ingestion | Python (BeautifulSoup + requests) |

## Project Structure

```
27-NextLeap-2026/
├── docs/                  # PRD, architecture, implementation guide
├── data/
│   ├── sources.csv        # 5 HDFC scheme URLs
│   └── snapshots/         # Offline page snapshots (gitignored)
├── chroma/                # Vector store (gitignored)
├── src/
│   ├── ingest/            # Load → Chunk → Embed → Store
│   │   ├── load.py
│   │   ├── chunk.py
│   │   ├── embed_store.py
│   │   └── run_ingest.py   # CLI entry
│   ├── retrieve/          # Runtime pipeline
│   │   ├── retriever.py
│   │   ├── guardrails.py
│   │   ├── generate.py
│   │   └── orchestrator.py
│   ├── app/
│   │   └── ui.py          # Streamlit UI
│   └── config.py          # Shared config
├── render.yaml            # Render deployment config
├── start.sh               # Startup script for Render
└── requirements.txt
```

## Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/Gursimaran21/RAG-based-Mutual-Fund-FAQ-Chatbot.git
cd RAG-based-Mutual-Fund-FAQ-Chatbot
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini
```

### 4. Run ingestion

```bash
python -m src.ingest.run_ingest --reset
```

This fetches (or reads snapshots of) the 5 Groww pages, chunks them, embeds with MiniLM, and stores in ChromaDB.

### 5. Launch the app

```bash
streamlit run src/app/ui.py
```

Open `http://localhost:8501` in your browser.

## Deploy on Render

1. Push to GitHub (already done)
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo
4. Render auto-detects `render.yaml`
5. Add `OPENAI_API_KEY` in the dashboard
6. Deploy

The app will be live at `https://hdfc-mf-faq-chatbot.onrender.com`.

## RAG Pipeline

```
Load → Chunk → Embed → Store → Retrieve → Generate → Cite
```

| Stage | Module | Description |
|-------|--------|-------------|
| Load | `src/ingest/load.py` | Fetch/read 5 Groww pages |
| Chunk | `src/ingest/chunk.py` | RecursiveCharacterTextSplitter (600 chars, 100 overlap) |
| Embed | `src/ingest/embed_store.py` | MiniLM embeddings |
| Store | `src/ingest/embed_store.py` | ChromaDB persistent collection |
| Retrieve | `src/retrieve/retriever.py` | Top-k similarity search |
| Guardrails | `src/retrieve/guardrails.py` | Block advice, PII, performance |
| Generate | `src/retrieve/generate.py` | Grounded LLM answer + citation |

## Sample Questions

**Factual (will answer):**
- "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
- "What is the lock-in period for HDFC ELSS Tax Saver?"
- "What is the exit load on HDFC Small Cap Fund Direct Growth?"

**Refused (advice/PII/performance):**
- "Should I buy HDFC Small Cap?"
- "Which fund will give the highest returns?"
- "My PAN is ABCDE1234F — what's the expense ratio?"

## Known Limitations

- Only 5 HDFC Direct-Growth schemes are covered
- No investment advice, suitability analysis, or return predictions
- Requires an OpenAI-compatible API key for generation
- ChromaDB is local; the index is rebuilt on each deploy
- Snapshots may become outdated; verify on official sources

## License

Demo/educational project.
