# HDFC Mutual Fund FAQ Chatbot

A **facts-only RAG chatbot** that answers factual questions about HDFC mutual fund schemes using a fixed corpus of 6 public Groww pages plus a procedural FAQ knowledge base. Every answer cites one source URL. Investment advice and performance predictions are refused.

## Features

- **Retrieval-Augmented Generation (RAG)** pipeline with visible stages
- **Facts-only answers** (max 3 sentences) with one citation per response
- **Guardrails** that refuse advice, performance comparisons, and PII
- **Conversational memory** (last 4 messages) for follow-up questions
- **Streamlit UI** with welcome message, disclaimer, and 3 example questions
- **ChromaDB** local vector store with MiniLM embeddings (no API rate limits)
- **FAQ knowledge base** for procedural queries (statements, taxation, etc.)
- **Graceful fallback** — always returns an answer, never shows error messages

## Tech Stack

| Layer | Technology |
|-------|------------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (local, no API limits) |
| Vector DB | ChromaDB (pre-built, committed to repo) |
| LLM | Google Gemini via OpenAI-compatible API (`gemini-3.5-flash-lite`) |
| UI | Streamlit |
| Ingestion | Python (BeautifulSoup + requests) |

## Project Structure

```
27-NextLeap-2026/
├── docs/                  # PRD, architecture, implementation guide
├── data/
│   ├── sources.csv        # 6 HDFC scheme URLs
│   ├── faq.csv            # Procedural Q&A (statements, tax, etc.)
│   └── snapshots/         # Offline page snapshots (gitignored)
├── chroma/                # Pre-built vector store (committed to repo)
├── src/
│   ├── ingest/            # Load → Chunk → Embed → Store
│   │   ├── load.py
│   │   ├── chunk.py       # Includes structured fact extraction
│   │   ├── embed_store.py
│   │   └── run_ingest.py   # CLI entry
│   ├── retrieve/          # Runtime pipeline
│   │   ├── retriever.py
│   │   ├── guardrails.py
│   │   ├── generate.py    # LLM + fallback logic
│   │   └── orchestrator.py
│   ├── app/
│   │   └── ui.py          # Streamlit UI
│   └── config.py          # Shared config
├── warmup.py              # Pre-load embedding model (cold-start fix)
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
GEMINI_API_KEY=your-gemini-api-key-here
LLM_MODEL=gemini-3.5-flash-lite
```

Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/apikey).

### 4. Run ingestion (optional — pre-built index is committed)

```bash
python -m src.ingest.run_ingest --reset
```

This fetches (or reads snapshots of) the 6 Groww pages, chunks them, embeds with MiniLM, and stores in ChromaDB. The pre-built `chroma/` directory is already committed to the repo, so this step is only needed if you want to refresh the data.

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
5. Add `GEMINI_API_KEY` in the dashboard
6. Deploy

The app will be live at `https://hdfc-mf-faq-chatbot.onrender.com`.

## RAG Pipeline

```
Load → Chunk → Embed → Store → Retrieve → Generate → Cite
```

| Stage | Module | Description |
|-------|--------|-------------|
| Load | `src/ingest/load.py` | Fetch/read 6 Groww pages |
| Chunk | `src/ingest/chunk.py` | RecursiveCharacterTextSplitter (400 chars, 80 overlap) + structured fact extraction |
| Embed | `src/ingest/embed_store.py` | MiniLM embeddings (local, no API limits) |
| Store | `src/ingest/embed_store.py` | ChromaDB persistent collection |
| Retrieve | `src/retrieve/retriever.py` | Top-k similarity search (k=8) |
| Guardrails | `src/retrieve/guardrails.py` | Block advice, PII, performance |
| Generate | `src/retrieve/generate.py` | Grounded LLM answer + citation + fallback |

## Sample Questions

**Factual (will answer):**
- "What is the expense ratio of HDFC Small Cap Fund Direct Growth?"
- "What is the lock-in period for HDFC ELSS Tax Saver?"
- "What is the exit load on HDFC Top 100 Fund Direct Growth?"
- "What is the minimum SIP amount for HDFC Flexi Cap Fund?"
- "What is the benchmark index for HDFC Mid Cap Fund Direct Growth?"
- "What is the risk rating of HDFC Balanced Advantage Fund?"

**Procedural (FAQ):**
- "How to download capital-gains statement?"
- "How to download account statement?"
- "How are mutual fund returns taxed?"

**Refused (advice/PII/performance):**
- "Should I buy HDFC Small Cap?"
- "Which fund will give the highest returns?"
- "My PAN is ABCDE1234F — what's the expense ratio?"

## Known Limitations

- Only 6 HDFC Direct-Growth schemes are covered
- No investment advice, suitability analysis, or return predictions
- Requires a Gemini API key for generation (free tier available)
- ChromaDB is local; the pre-built index is committed to the repo
- Snapshots may become outdated; verify on official sources

## Disclaimer

> **Facts-only. No investment advice.** Answers are based on public scheme pages and may change. Verify on the official source before acting.

## License

Demo/educational project.
