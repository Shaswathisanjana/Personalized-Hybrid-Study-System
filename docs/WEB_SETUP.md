# Independent PHSS Web App

This checkout uses its own Python environment, frontend dependencies and SQLite database. It does not import the original PHSS_Git checkout. Never point its store at the original student database.

## Start the built application

From this folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open http://127.0.0.1:8000 . React production assets are served by FastAPI. API documentation: http://127.0.0.1:8000/docs . No second frontend server is needed for this mode.

## Configure providers

Copy .env.example to .env in THIS folder only and fill your own keys. GEMINI_API_KEY enables existing routing, lessons, semantic assessment and analysis. YOUTUBE_API_KEY enables YouTube resources. OPENALEX_API_KEY is optional depending on the academic provider's access requirements. Restart the backend after editing. No credentials are included. Missing configuration or provider failures never produce fabricated successful AI output.

## Frontend development

```powershell
npm.cmd --prefix frontend run dev
```

Vite serves http://127.0.0.1:5173 and proxies /api to port 8000. Use npm.cmd on Windows if npm.ps1 is blocked by execution policy.

## Reinstall independent dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
```

Do not run these commands in PHSS_Git. The setup here is separate from that environment.

## Manual checks

1. Create/select a local profile. Ask "Teach me recursion". Read the lesson, start practice, submit an actual answer, then refresh and continue studying.
2. Ask "Give me a coding problem on linked lists". Wait for a validated generated package. Edit original code, Save draft, request a hint, submit, inspect tests and optionally verify a correction. Draft saving is explicit.
3. Ask "Find research papers about agentic AI". Adjust search target, select multiple real results and add them to the collection. Fetch additional pages explicitly. Abstract-only labels remain visible.
4. Ask "Compare my uploaded research papers". Upload PDFs, run bounded extraction batches, then bounded analysis batches. Inspect page/chunk claims, comparisons and suggestions. Select report sections and download Word and Markdown reports.
5. Ask "Teach me recursion and then give me coding practice". Complete assessed learning, continue, and inspect coding preparation using the updated shared CACM.
6. Use Professor demo to inspect the actual plan, policies and genuine conflicts. Resolve conflicts through the displayed diagnostic when conflicting evaluated evidence exists.
7. Create a second profile and verify it has separate progress, papers and saved activities.

## Provider call limits

The web server configures the existing Gemini SDK clients with at most a 60-second transport timeout and two SDK attempts per request, preserving shorter configured timeouts. Existing agent-level retries still apply; this is a per-request bound, not a guaranteed total activity deadline. Research pages/chunks and generated exercise attempts retain their existing limits. Only an explicit action initiates provider work.

## Boundaries

Local desktop/demo application, not production authentication or a multi-worker deployment. UUID profiles are not logins. Run trusted Python code only: inherited subprocess execution is not a hostile-code sandbox. Mastery remains rule-based and uncalibrated by real-student studies. External provider availability and paid live behavior require your credentials and have not been asserted by offline tests. Extracted PDF text has no OCR. Report gaps/directions are suggestions, not established findings. All costs and processing limits inherited from service policies remain visible where applicable.

Offline fixture server tools/web_fixture_server.py is exclusively for tests, uses a separate fixture database and is never started by start_web.ps1. Browser screenshots and test reports from that server use synthetic sources. Do not present those sources as real academic retrieval.
