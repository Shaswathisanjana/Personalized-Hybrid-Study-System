# 🔬 PHSS Research Assistant — Multi-Agent AI Module

> **Personalized Hybrid Study System (PHSS)** — Research Assistant  
> Built with LangGraph · ChromaDB · Google Gemini · Streamlit  
> **100% Free to run** — no credit card, no paid APIs

---

## 📋 Table of Contents

1. [What This Does](#-what-this-does)
2. [System Architecture](#-system-architecture)
3. [How Each Agent Works](#-how-each-agent-works)
4. [API Keys — What You Need](#-api-keys--what-you-need)
5. [Installation Step-by-Step](#-installation-step-by-step)
6. [Running the App](#-running-the-app)
7. [Folder Structure](#-folder-structure)
8. [Environment Variables Reference](#-environment-variables-reference)
9. [API Endpoints](#-api-endpoints-fastapi-backend)
10. [Running Tests](#-running-tests)
11. [Troubleshooting](#-troubleshooting)

---

## 🧠 What This Does

The PHSS Research Assistant is a **multi-agent AI pipeline** that automates the entire academic research workflow:

1. **You type a research topic** (e.g. _"Generate a report on federated learning in healthcare"_)
2. **9 AI agents collaborate automatically:**
   - 🔍 Searches 3 academic databases (arXiv, Semantic Scholar, OpenAlex)
   - 📖 Reads and extracts key knowledge from papers
   - 📝 Writes a full literature review
   - 🔬 Identifies research gaps with evidence
   - 💡 Proposes future research directions
   - ✍️ Assembles a complete structured report
   - 📚 Formats citations (IEEE, APA, BibTeX)
3. **You get a downloadable report** in Markdown, DOCX, and PDF
4. **Ask follow-up questions** via the RAG-powered Q&A chat

---

## 🏗️ System Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                    Manager Agent                         │
│  (Intent classification → Pipeline routing)             │
└─────────────────┬───────────────────────────────────────┘
                  │  Selects pipeline based on intent
                  ▼
┌─────────────────────────────────────────────────────────┐
│                  LangGraph Pipeline                      │
│                                                         │
│  Search Agent → Reading Agent → Lit Review Agent        │
│       │              │               │                  │
│       ▼              ▼               ▼                  │
│  [arXiv,       [PDF Parser,    [LLM Synthesis]          │
│  Semantic      Extractor,                               │
│  Scholar,      Embedder]      Gap Detection Agent       │
│  OpenAlex]          │               │                  │
│       │             ▼               ▼                  │
│       └──────► ChromaDB ◄─── Novelty Agent             │
│                 Vector Store         │                  │
│                                      ▼                  │
│                              Writing Agent              │
│                                      │                  │
│                                      ▼                  │
│                              Citation Agent             │
│                                      │                  │
│                              Export Pipeline            │
│                         (Markdown / DOCX / PDF)         │
└─────────────────────────────────────────────────────────┘
                  │
                  ▼
         Q&A Agent (RAG)
   (queries ChromaDB for grounded answers)
```

### Pipeline Routes (by Intent)

| User Intent | Pipeline Triggered |
|---|---|
| "find papers on X" | Search Agent only |
| "read papers on X" | Search → Reading |
| "write a literature review" | Search → Reading → Lit Review → Writing → Citation |
| "find research gaps" | Search → Reading → Lit Review → Gap Detection → Writing → Citation |
| "suggest future research" | Search → Reading → Lit Review → Gap → Novelty → Writing → Citation |
| "generate a full report" | Full pipeline (all agents) |
| Q&A question | Q&A Agent only (RAG from ChromaDB) |

---

## 🤖 How Each Agent Works

### 1. Manager Agent
- Receives your raw query
- Uses Gemini LLM to classify intent (e.g. `full_report`, `qa`, `gap_analysis`)
- Extracts the clean topic (e.g. _"federated learning in healthcare"_)
- Selects the correct ordered pipeline of agents to run
- **File:** `app/agents/manager/manager_agent.py`

### 2. Search Agent
- Searches 3 free databases in parallel:
  - **arXiv** — preprints (no key needed)
  - **Semantic Scholar** — academic papers (optional key for higher rate limits)
  - **OpenAlex** — open scholarly knowledge graph (no key needed)
- Deduplicates results by title similarity
- Returns a list of `PaperMetadata` objects
- **File:** `app/agents/search/search_agent.py`

### 3. Reading Agent
- For each paper found, tries to download the PDF
- Parses PDF text using PyMuPDF and pdfplumber
- Sends text to Gemini LLM with a structured extraction prompt
- Extracts: methodology, results, datasets, limitations, key concepts, contribution
- Embeds extracted knowledge into ChromaDB using local sentence-transformers
- **File:** `app/agents/reading/reading_agent.py`

### 4. Literature Review Agent
- Retrieves all paper extractions from ChromaDB
- Sends all summaries to Gemini LLM
- Returns structured JSON: introduction, existing approaches, method comparison, trends, strengths/weaknesses, chronological developments
- **File:** `app/agents/lit_review/lit_review_agent.py`

### 5. Gap Detection Agent
- Analyses paper extractions for what is missing or understudied
- Identifies gaps by type: `methodology_gap`, `dataset_gap`, `evaluation_gap`, `application_gap`, `theoretical_gap`
- Each gap includes: description, evidence (which papers), severity (high/medium/low), suggested direction
- **File:** `app/agents/gap_detection/gap_agent.py`

### 6. Novelty Agent
- Takes identified gaps as input
- Proposes concrete future research directions with reasoning
- Assesses feasibility and estimated impact for each idea
- **File:** `app/agents/novelty/novelty_agent.py`

### 7. Writing Agent
- Assembles all outputs into a full structured report
- Sections: Abstract, Introduction, Literature Review, Comparative Analysis, Research Gaps, Future Directions, Conclusion
- Saves report to ChromaDB and triggers the export pipeline
- Generates Markdown, DOCX, and PDF files in `./data/exports/`
- **File:** `app/agents/writing/writing_agent.py`

### 8. Citation Agent
- Takes paper metadata and formats citations in IEEE, APA, and BibTeX
- Adds inline citation numbers to the report body
- **File:** `app/agents/citation/citation_agent.py`

### 9. Q&A Agent (RAG)
- Accepts a question + report_id
- Queries ChromaDB for relevant context (top-k semantic search)
- Sends retrieved context + question to Gemini LLM
- **Strict rule: only answers from retrieved context** — no hallucination
- Supports modes: `general`, `explain_paper`, `compare_papers`, `summarize_section`, `explain_term`
- **File:** `app/agents/qa/qa_agent.py`

---

## 🔑 API Keys — What You Need

### ✅ Required (only 1 key)

**`GOOGLE_API_KEY`** — Powers all 9 agents via Gemini LLM

| Attribute | Detail |
|---|---|
| Cost | **FREE** — no credit card, no billing ever |
| Free tier | 1,500 requests/day, 15 req/minute |
| Signup | Any Google account (Gmail) |

**Steps to get your free Gemini API key:**
1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with any Google account
3. Click **"Create API Key"**
4. Select any project (or create a new one — it's free)
5. Copy the key — it looks like: `AIzaSyXXXXXXXXXXXXXXXXXX`

---

### ⬜ Optional Keys

| Key | Where to Paste | Why It Helps |
|---|---|---|
| `SEMANTIC_SCHOLAR_API_KEY` | `.env` file | Raises rate limit from 1 req/s to 100 req/s. Free signup at [semanticscholar.org/product/api](https://www.semanticscholar.org/product/api) |
| `CROSSREF_MAILTO` | `.env` file | Just your email. Used as a courtesy identifier for Crossref — no signup, no auth |

> **arXiv and OpenAlex** need **no keys at all** — they are fully open APIs.

---

## 💻 Installation Step-by-Step

### Prerequisites
- **Python 3.11+** — [download here](https://www.python.org/downloads/)
- Run all commands from: `d:\sem7\res_agent\`

---

### Step 1 — Open terminal in the project folder

```powershell
cd d:\sem7\res_agent
```

### Step 2 — Create a virtual environment

```powershell
python -m venv .venv
```

### Step 3 — Activate the virtual environment

```powershell
# PowerShell
.venv\Scripts\Activate.ps1

# OR Command Prompt
.venv\Scripts\activate.bat
```

✅ You should see `(.venv)` at the start of your terminal prompt.

### Step 4 — Install Poetry

```powershell
pip install poetry
```

### Step 5 — Install all project dependencies

```powershell
poetry install
```

> First run takes 3–5 minutes — it downloads LangChain, ChromaDB, sentence-transformers, Streamlit, etc.

### Step 6 — Create your `.env` file and add your API key

```powershell
copy .env.example .env
```

Open `.env` in Notepad or VS Code. Find this line:

```
GOOGLE_API_KEY=your-gemini-api-key-here
```

Replace it with your actual key:

```
GOOGLE_API_KEY=AIzaSyAbc123YourRealKeyHere
```

Save the file. That's the only change required.

### Step 7 — Create data directories

```powershell
New-Item -ItemType Directory -Force -Path data\chroma, data\exports, data\papers
```

---

## 🚀 Running the App

### Option A — Streamlit UI (Recommended for interactive use)

```powershell
streamlit run streamlit_app.py
```

Open browser at: **http://localhost:8501**

**4 pages in the UI:**
| Page | What It Does |
|---|---|
| 🏠 Home | Overview, example queries to click and run |
| 🔍 Research | Type a topic → run the full pipeline → see results |
| 📄 Report Viewer | Read the generated report section by section, download files |
| 💬 Q&A Chat | Ask questions about the report — RAG-grounded answers only |

---

### Option B — FastAPI REST API (for programmatic use)

```powershell
uvicorn app.main:app --reload --port 8000
```

- Interactive API docs: **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

---

## 📁 Folder Structure

```
res_agent/
│
├── .env                    ← YOUR API KEYS GO HERE (copy from .env.example)
├── .env.example            ← Template showing what keys are needed
├── pyproject.toml          ← Python dependencies (Poetry)
├── streamlit_app.py        ← Streamlit UI — run this for the web interface
│
├── app/
│   ├── main.py             ← FastAPI app entry point
│   │
│   ├── core/
│   │   ├── state.py        ← AgentState TypedDict (shared data between all agents)
│   │   ├── graph.py        ← LangGraph pipeline — wires all agents together
│   │   ├── router.py       ← Intent → pipeline routing logic
│   │   └── llm.py          ← Gemini LLM factory (change model name here)
│   │
│   ├── agents/
│   │   ├── manager/        ← Intent classification & routing
│   │   ├── search/         ← arXiv, Semantic Scholar, OpenAlex search
│   │   │   └── sources/    ← One file per search source
│   │   ├── reading/        ← PDF parsing, LLM extraction, ChromaDB embedding
│   │   ├── lit_review/     ← Literature review synthesis
│   │   ├── gap_detection/  ← Research gap identification
│   │   ├── novelty/        ← Future research direction proposals
│   │   ├── writing/        ← Report assembly + export trigger
│   │   ├── citation/       ← IEEE/APA/BibTeX citation formatting
│   │   └── qa/             ← RAG Q&A (ChromaDB + Gemini)
│   │
│   ├── api/
│   │   ├── research.py     ← POST /api/research/
│   │   ├── qa.py           ← POST /api/qa/
│   │   └── export.py       ← GET /api/export/{report_id}
│   │
│   ├── knowledge_base/
│   │   └── chroma_client.py ← ChromaDB wrapper (store, retrieve, semantic search)
│   │
│   ├── export/
│   │   ├── markdown_exporter.py
│   │   ├── docx_exporter.py
│   │   └── pdf_exporter.py
│   │
│   └── models/
│       ├── paper.py        ← PaperMetadata, ExtractedPaperInfo
│       ├── review.py       ← LiteratureReview, MethodComparison
│       ├── report.py       ← ResearchReport, ResearchGap, Citation
│       └── qa.py           ← QARequest, QAResponse
│
├── configs/
│   └── settings.py         ← All config loaded from .env via pydantic-settings
│
├── data/                   ← Auto-created on first run
│   ├── chroma/             ← ChromaDB vector store (local, persistent)
│   ├── exports/            ← Generated report files (MD, DOCX, PDF)
│   └── papers/             ← Cached paper PDFs
│
└── tests/
    ├── unit/               ← Fast unit tests (mock all external APIs)
    └── integration/        ← Full pipeline tests (require real API key)
```

---

## ⚙️ Environment Variables Reference

File: `.env` (in the project root `d:\sem7\res_agent\.env`)

```env
# ─── REQUIRED — get free at aistudio.google.com/app/apikey ──────
GOOGLE_API_KEY=AIzaSy...

# ─── OPTIONAL — improves Semantic Scholar rate limits ────────────
SEMANTIC_SCHOLAR_API_KEY=

# ─── OPTIONAL — polite identifier for Crossref API ──────────────
CROSSREF_MAILTO=you@example.com

# ─── LLM SETTINGS ───────────────────────────────────────────────
PRIMARY_LLM=gemini-2.0-flash       # Free model (1500 req/day)
FALLBACK_LLM=gemini-1.5-flash      # Backup if primary fails

# ─── EMBEDDINGS (local, no API needed) ──────────────────────────
EMBEDDING_MODEL=all-MiniLM-L6-v2   # ~22MB, downloaded once, runs offline

# ─── LOCAL STORAGE ──────────────────────────────────────────────
CHROMA_PERSIST_DIR=./data/chroma
EXPORT_DIR=./data/exports
PAPER_CACHE_DIR=./data/papers

# ─── APP CONFIG ─────────────────────────────────────────────────
APP_ENV=development
LOG_LEVEL=INFO
MAX_PAPERS_PER_SEARCH=20
```

---

## 🌐 API Endpoints (FastAPI Backend)

Start server: `uvicorn app.main:app --reload --port 8000`
Interactive docs: **http://localhost:8000/docs**

### `POST /api/research/` — Run full research pipeline
```bash
curl -X POST http://localhost:8000/api/research/ \
  -H "Content-Type: application/json" \
  -d '{"query": "Generate a report on federated learning in healthcare"}'
```

### `POST /api/qa/` — Ask a question about a report
```bash
curl -X POST http://localhost:8000/api/qa/ \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report_abc123",
    "question": "What datasets were most commonly used?",
    "mode": "general"
  }'
```
Modes: `general` · `explain_paper` · `compare_papers` · `summarize_section` · `explain_term`

### `GET /api/export/{report_id}?format=pdf` — Download report
```bash
curl "http://localhost:8000/api/export/report_abc123?format=pdf"    -o report.pdf
curl "http://localhost:8000/api/export/report_abc123?format=docx"   -o report.docx
curl "http://localhost:8000/api/export/report_abc123?format=markdown" -o report.md
```

### `GET /health` — Health check
```bash
curl http://localhost:8000/health
# → {"status": "ok", "service": "PHSS Research Assistant"}
```

---

## 🧪 Running Tests

```powershell
# Run all unit tests
pytest tests/unit/ -v

# Run a specific file
pytest tests/unit/test_search_agent.py -v

# Show print output
pytest tests/unit/ -v -s
```

Unit tests mock all external APIs so they run offline and instantly.

---

## 🔧 Troubleshooting

### `GOOGLE_API_KEY is missing or invalid`
- Ensure `.env` exists at `d:\sem7\res_agent\.env`
- Line must look exactly like: `GOOGLE_API_KEY=AIzaSyYOURKEY` (no quotes, no spaces around `=`)

### `ModuleNotFoundError: No module named 'app'`
- Activate the venv: `.venv\Scripts\Activate.ps1`
- Run commands from `d:\sem7\res_agent\` (not a subdirectory)

### PowerShell `cannot be loaded because running scripts is disabled`
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Slow first run (sentence-transformers)
Normal — the `all-MiniLM-L6-v2` model (~22 MB) downloads once. Subsequent runs are instant.

### `WeasyPrint` PDF export fails on Windows
WeasyPrint needs GTK3 on Windows. Options:
- Install GTK3: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
- Use Markdown or DOCX export instead (always works, no extra dependencies)

### Gemini `429 Too Many Requests`
- Free tier: 15 requests/minute — wait 60 seconds and retry
- Reduce load: set `MAX_PAPERS_PER_SEARCH=5` in `.env`

---

## 💡 Cost Breakdown

| Component | Technology | Cost |
|---|---|---|
| LLM (all agents) | Google Gemini 2.0 Flash | **$0** — 1,500 req/day free |
| Embeddings | sentence-transformers (local CPU) | **$0** — runs offline |
| Vector DB | ChromaDB (embedded, local disk) | **$0** — no server needed |
| Paper search | arXiv + OpenAlex | **$0** — open APIs |
| Paper search | Semantic Scholar | **$0** — free public API |
| PDF parsing | PyMuPDF + pdfplumber | **$0** — open source |
| DOCX export | python-docx | **$0** — open source |

**Total monthly cost: $0.00** 🎉
