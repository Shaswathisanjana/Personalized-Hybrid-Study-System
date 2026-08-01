# Multi-Agent Research Platform 
### LLM: Google Gemini free tier — no local model, no paid API

## What's working end-to-end
- **Orchestrator** — keyword-based routing to the right agent
- **Research Agent** — topic → Semantic Scholar search → LLM summarization (Gemini 2.5 Flash, free tier) → markdown comparison table, all backed by a Chroma vector store (RAG)
- **Dashboard** — real (not mocked) counts pulled from the vector store: papers indexed, queries by topic

Two things touch the network: Semantic Scholar (paper search) and the Gemini API (summarization). Both are free — Semantic Scholar needs no key, Gemini needs a free key from Google AI Studio (no credit card).

## Planned / Phase 2 (described in slides, not built)
- Education Agent (learning roadmaps, course recommendations)
- Coding/debugging agent
- Full adaptive analytics
- Multi-turn conversational memory across agents

## Setup

### 1. Get a free Gemini API key
1. Go to https://aistudio.google.com/apikey
2. Sign in with a Google account, click "Create API key" (no credit card required)
3. Copy the key

```bash
export GEMINI_API_KEY=...
```

Free tier limits (as of mid-2026, may change — check https://ai.google.dev/gemini-api/docs/rate-limits): roughly 10 requests/minute and hundreds of requests/day on `gemini-2.5-flash`, which is more than enough for a demo. If you hit `429` rate-limit errors during heavy testing, switch `MODEL` in `backend/services/llm.py` to `"gemini-2.5-flash-lite"` for a higher-throughput, slightly lower-quality option.

### 2. Python environment
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
`chromadb` + `sentence-transformers` still pull in some ML libraries for local embeddings (used for RAG storage, not the LLM), so this install still takes a couple of minutes — but there's no multi-GB model download like Ollama required.

### 3. (Optional) Semantic Scholar API key
Not required, but raises your rate limit — see https://www.semanticscholar.org/product/api
```bash
export SEMANTIC_SCHOLAR_API_KEY=...
```

**No LLM installed locally, no GPU/RAM requirements for inference.**

## Run

Terminal 1 (backend):
```bash
uvicorn backend.main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
streamlit run frontend/app.py
```

Then open the Streamlit URL it prints (usually http://localhost:8501).

## Try it
Enter a topic like `retrieval augmented generation for code review` and hit Run.
Expect ~10-20s for the first call (paper fetch + Gemini summarization of each paper).

## Architecture

```
User
  │
  ▼
Streamlit frontend
  │  POST /query
  ▼
FastAPI backend
  │
  ▼
Orchestrator  ──(keyword routing)──▶  Research Agent
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                            ▼
                    Semantic Scholar API           Gemini API (free tier)
                    (paper search, no key)         (summarize + table, free key)
                              │
                              ▼
                    Chroma vector store (local)
                    (RAG + dashboard data)
```

## Notes for the zeroth review demo
- Set `GEMINI_API_KEY` and test a full run at least once before the review — don't
  discover a quota/region issue live.
- Free tier is rate-limited (requests/minute and requests/day) — if you're rehearsing
  a lot right before the demo, you could hit a temporary `429`. Add a short pause
  between test runs, or note this as a legitimate "Phase 2: apply for higher quota /
  add fallback model" line on your feasibility slide.
- Record a backup screen-capture of a successful run in case wifi drops or you hit
  a rate limit during the live demo.
- If Semantic Scholar rate-limits you (no API key = shared pool), mention: "Phase 2:
  apply for a Semantic Scholar API key / add arXiv as a fallback source."

## Troubleshooting
- **`PermissionDenied` / 403 from Gemini** → `GEMINI_API_KEY` isn't set or is invalid.
  Re-check `echo $GEMINI_API_KEY` in the terminal running uvicorn.
- **`429 RESOURCE_EXHAUSTED`** → you've hit the free-tier rate limit. Wait a minute,
  or switch to `gemini-2.5-flash-lite` in `backend/services/llm.py`.
- **Summaries look truncated** → raise `max_output_tokens` in the `_generate` calls
  in `backend/services/llm.py`.
- **`ModuleNotFoundError: google.genai`** → you're on the old deprecated
  `google-generativeai` package. Make sure `pip install -r requirements.txt` picked
  up `google-genai` (check with `pip show google-genai`).
