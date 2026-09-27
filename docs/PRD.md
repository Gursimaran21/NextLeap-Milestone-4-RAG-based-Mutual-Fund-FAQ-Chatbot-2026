# PRD: Mutual Fund Facts-Only RAG Chatbot

**Product:** HDFC Mutual Fund FAQ Assistant  
**Audience:** Class demo / milestone prototype  
**Status:** Draft  
**Last updated:** 2026-09-27

---

## 1. Summary

Build a small **RAG (Retrieval-Augmented Generation) chatbot** that answers **factual questions only** about selected HDFC mutual fund schemes using a fixed corpus of public Groww pages. Every answer must cite one source link. The assistant must refuse investment advice and never invent numbers.

This is a **working class demo**, not a production product: clear pipeline stages, a tiny UI, and submission-ready deliverables.

---

## 2. Problem

Retail users and support/content teams repeatedly ask the same scheme facts (expense ratio, exit load, SIP minimum, ELSS lock-in, riskometer, benchmark, how to get statements). Answers must come from **official/public scheme pages**, with transparent citations—not blogs, screenshots of private backends, or model speculation.

---

## 3. Goals (class demo)

| Priority | Goal |
|----------|------|
| P0 | End-to-end RAG: Load → Chunk → Embed → Store → Retrieve → Answer |
| P0 | Facts-only answers with **one citation URL** per response |
| P0 | Refuse buy/sell/advice questions politely |
| P0 | Tiny chat UI with welcome, 3 example questions, and disclaimer |
| P1 | Answers ≤3 sentences + “Last updated from sources: …” |
| P1 | Submission pack: README, source list, sample Q&A, disclaimer |

**Non-goals**

- Portfolio advice, suitability, or “should I invest?”
- Computing/comparing returns or rankings
- Multi-AMC coverage or live market APIs
- Auth, user accounts, or storing PII
- Production-grade scraping, monitoring, or fine-tuning

---

## 4. Users & use cases

**Primary users (demo):** Instructor / classmates reviewing the prototype.

**Implied end users:** Retail users comparing schemes; support teams answering repetitive MF FAQs.

**In-scope example queries**

- What is the expense ratio of HDFC Large Cap Fund (Direct–Growth)?
- What is the exit load?
- What is the minimum SIP amount?
- What is the ELSS lock-in for HDFC Tax Saver?
- What is the riskometer / benchmark?
- How do I download a capital-gains / statement document? (facts + link only)

**Out-of-scope example queries (must refuse)**

- Should I buy / sell this fund?
- Which fund is best for me?
- Will this beat the market?
- Compare which one will give higher returns (performance claims)

---

## 5. Scope

### 5.1 Corpus

**AMC:** HDFC Mutual Fund  
**Plans:** Direct–Growth (5 schemes, one per category)

| Category | Scheme (Groww page) |
|----------|---------------------|
| Large Cap | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| Flexi Cap | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| ELSS | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| Small Cap | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| Balanced Advantage (Hybrid) | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

**Source rules:** Public pages only. Prefer AMC / SEBI / AMFI / Groww scheme pages listed above. No third-party blogs as citations.

### 5.2 Product surface

- **Welcome line** + **3 example questions**
- Chat input + answer area
- Persistent UI note: **“Facts-only. No investment advice.”**
- Each answer: short fact text + **one source link** + source freshness note

---

## 6. Functional requirements

| ID | Requirement |
|----|-------------|
| FR-1 | Ingest the 5 fixed URLs into a local vector store |
| FR-2 | Retrieve top-k relevant chunks for a user question |
| FR-3 | Generate an answer grounded only in retrieved chunks |
| FR-4 | Always append exactly one citation URL (best matching source page) |
| FR-5 | Detect advice/opinion queries and refuse with a polite facts-only message + educational link when possible |
| FR-6 | Reject / ignore PII (PAN, Aadhaar, account numbers, OTPs, emails, phones)—do not store them |
| FR-7 | If asked for returns/performance, do not compute; point to official factsheet / scheme page |
| FR-8 | Keep answers ≤3 sentences when answering facts |
| FR-9 | Include “Last updated from sources: &lt;date or crawl timestamp&gt;” |

---

## 7. Technical architecture (RAG stages)

Demo must make each stage visible in code/README (ingestion vs retrieval).

```
[Public pages]
      │
      ▼
  LOADING  → fetch/parse text from 5 URLs (or saved snapshots)
      │
      ▼
  CHUNKING → split into retrieval units
      │
      ▼
  EMBEDDING → sentence-transformers/all-MiniLM-L6-v2
      │
      ▼
  STORE    → ChromaDB (vector + metadata: url, scheme, section)
      │
      ▼
  RETRIEVE → similarity search (top-k)
      │
      ▼
  GENERATE → LLM answers from context only + cite source
```

### 7.1 Stack (locked for demo)

| Layer | Choice |
|-------|--------|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (Hugging Face) |
| Vector DB | ChromaDB |
| Chunking | **Recursive character splitting** (see §7.2) |
| App | Lightweight chat UI (Streamlit / Gradio / simple web—team choice) |

### 7.2 Chunking strategy (decision)

**Decision for this corpus: RecursiveCharacterTextSplitter** (not pure semantic chunking).

**Why**

- Groww scheme pages are **sectioned factual text** (fees, loads, SIP, risk, etc.), not long narrative essays.
- Recursive splitting on `\n\n`, `\n`, `. ` preserves headings/paragraphs well enough for MiniLM + Chroma.
- Simpler, deterministic, and easier to debug in a class demo than embedding-based semantic chunking.
- Semantic chunking is optional later if retrieval quality is weak on boundary questions.

**Suggested defaults (tunable during build)**

- `chunk_size`: ~500–800 characters  
- `chunk_overlap`: ~80–120 characters  
- Metadata per chunk: `source_url`, `scheme_name`, `category`

---

## 8. UX / content requirements

**Disclaimer (must appear in UI)**

> Facts-only. No investment advice. Answers are based on public scheme pages and may change. Verify on the official source before acting.

**Answer shape**

1. 1–3 factual sentences grounded in context  
2. Source: `&lt;one URL&gt;`  
3. Last updated from sources: `&lt;timestamp&gt;`

**Refusal shape**

- Polite decline of advice  
- Offer to answer a factual parameter instead  
- Optional educational / scheme FAQ link from corpus

---

## 9. Constraints & compliance

- **Public sources only** — no private app backends, no blog citations  
- **No PII** — do not accept or store PAN, Aadhaar, accounts, OTPs, emails, phones  
- **No performance claims** — no computed/compared returns  
- **Transparency** — short answers + citation + source freshness  
- **Demo realism** — pipeline stages must be identifiable in architecture/docs

---

## 10. Deliverables (submission)

| Deliverable | Description |
|-------------|-------------|
| Working prototype | App link **or** ≤3-min demo video if hosting isn’t possible |
| Source list | CSV or MD with the 5 URLs used |
| README | Setup steps, scope (AMC + schemes), known limits |
| Sample Q&A | 5–10 queries with assistant answers + links |
| Disclaimer | Exact UI disclaimer snippet |

---

## 11. Success criteria (demo day)

- [ ] Asking “expense ratio / exit load / min SIP / ELSS lock-in” returns a grounded fact + correct scheme URL  
- [ ] Asking “should I buy?” is refused without recommendations  
- [ ] Asking for returns does not invent numbers; redirects to official page  
- [ ] UI shows welcome, 3 examples, and facts-only disclaimer  
- [ ] README documents Load → Chunk → Embed → Store → Retrieve clearly  
- [ ] All five submission artifacts listed in §10 are present  

---

## 12. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| Groww page layout changes / scrape blocks | Save HTML/text snapshots at ingest time; cite static snapshot date |
| Hallucinated numbers | Strict prompt: answer only from context; if missing, say “not found in sources” |
| Weak retrieval | Tune chunk size/overlap; filter by `scheme_name` metadata when query names a fund |
| Scope creep (advice, comparisons) | Hard refuse list + system prompt |

---

## 13. Out of scope for v1 (explicit)

- Multi-turn portfolio planning  
- Live NAV charts or return calculators  
- User login / KYC flows  
- More than 5 schemes or other AMCs  
- Fine-tuned custom embedding models  

---

## 14. Open decisions (implementation)

- Chat UI framework (Streamlit vs Gradio vs custom)  
- LLM provider for generation (local vs API)—must still be grounded in retrieved context  
- Whether to ship offline snapshots of the 5 pages for reliable demos  

---

## Appendix A — Example starter questions (UI)

1. What is the expense ratio of HDFC Large Cap Fund Direct Growth?  
2. What is the lock-in period for HDFC ELSS Tax Saver?  
3. What is the exit load on HDFC Small Cap Fund Direct Growth?
