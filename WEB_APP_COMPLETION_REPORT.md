# PHSS Web App delivery: stages 3-8

The independent application is implemented at `C:/Users/DELL/OneDrive/Documents/PHSS_Web_App`. React production assets are served by FastAPI at http://127.0.0.1:8000 . The original PHSS_Git source and environment were not edited. No commit, push, reset, clean or discard operation was performed.

## What was implemented

- React + TypeScript + Vite with Tailwind v4, Radix UI primitives, a responsive green/cream design system, loading states, recoverable errors and local Monaco Python editing.
- Student home with one common query input, real progress summaries, topic browser, recent assessed activities and continue-studying access.
- Inline Learning, Coding and Research activities using the existing Python services and autonomous orchestrator. No JavaScript agent algorithms and no generic chatbot replacement.
- Owner-scoped bounded multi-step plans, contextual clarification, preparation/retry/continuation, genuine conflict intervention and diagnostic resolution.
- Personalized learning, actual resources, adaptive practice, misconception-aware shared state and the existing study planner.
- Curated and generated Python exercises, original-code evaluation, progressive hints, verified correction review, explicit draft persistence and assessment deduplication.
- Configurable academic search targets, incremental retrieval, persistent result selection, duplicate handling, multiple PDFs, actual extraction, bounded analysis and partial-failure recovery.
- Mixed-source collections with abstract-only/full-text labels, page/chunk claims, real methodology comparison, field-based evidence synthesis, preliminary gaps/directions, research comprehension, selectable DOCX sections and Markdown downloads.
- Independent SQLite persistence, profile separation, refresh/process-restart recovery, saved pending requests and existing cognitive receipt boundaries.
- Local-only startup and a separate offline browser fixture server. SDK timeout policy caps normal Gemini transport requests at 60 seconds and two SDK attempts while retaining shorter existing timeouts; agent-level retries remain.

## Exact files

`WEB_FILES_CHANGED.json` lists every created source/documentation file and modified copied file. Only these copied files were changed: `.gitignore`, `README.md`, `requirements.txt`. All copied `app/` agent, orchestrator, cognitive and persistence algorithms remain byte-for-byte unchanged. The copied README is retained as `docs/LEGACY_STREAMLIT_README.md`.

New implementation is in `backend/`, `frontend/`, `start_backend.ps1`, `start_web.ps1`, `requirements-lock.txt`, web documentation and web verification tools. Generated environments, node_modules, production build assets, browser screenshots, test reports and synthetic fixture databases are listed separately from source in the change manifest.

## Commands and actual verification

| Check | Actual result |
| --- | --- |
| Independent Python environment | `python -m venv .venv`; pip installed existing requirements plus FastAPI, Uvicorn, multipart support, httpx and pytest in the new folder only |
| Dependency consistency | `pip check`: no broken requirements; `requirements-lock.txt` records installed Python versions |
| Frontend dependencies | `npm.cmd install` in frontend; package-lock.json retained |
| TypeScript and production build | `npm.cmd --prefix frontend run build`: passed; editor is lazy-loaded but its bundle remains approximately 2.75 MB uncompressed |
| API integration | `python -B -m pytest backend/tests -q --tb=short --junitxml=data/web-api-final-results.xml`: **18 passed**, one Starlette/httpx deprecation warning |
| Browser end-to-end | `npx.cmd playwright test` in frontend: **7 passed** in the successful complete run; final rerun artifacts at data/web-e2e/results.json |
| Real application browser startup | `node tools/verify_real_web.mjs`: React/FastAPI loaded, zero browser JavaScript errors, empty production profile database, provider_configured=false |
| Python tooling | `python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline -q`: **13 passed** |
| Full inherited offline suite | `python -B tools/evaluate_offline.py`: **63/67 cases passed**, with 202 unittest executions and 41 script cases; zero skips |
| Isolated regression reruns | All four initially failing cases subsequently passed without changing tests or limits; details below |
| Original app | Original `python -B run_phss.py --check` passed; original `python -B tools/smoke_startup.py` returned HTTP health ok |
| New retained Streamlit dependencies | New environment's `python -B run_phss.py --check` passed |
| Source protection | All **318 original copied-source SHA-256 values** matched the Stage 1/2 manifest on verification |

Full-run artifact: `data/evaluation/20261020T181237596496Z/`. Initial failures were `test_open_topic_coding`, `test_open_topic_coding_streamlit`, `test_verified_coding_catalog` and `test_correction_verifier.py`. Logs show subprocess validation timeouts, correction timeout assertions and extra generated-package retries under load.

Serial reruns:
- `test_open_topic_coding_streamlit`: 4 tests passed, `data/evaluation/20261020T183246805997Z/`.
- `test_verified_coding_catalog`: 10 tests passed, `data/evaluation/20261020T183306536912Z/`.
- `test_correction_verifier.py`: script passed, `data/evaluation/20261020T183321178821Z/`.
- `test_open_topic_coding`: 16 tests passed on the final isolated run, `data/evaluation/20261020T183402681198Z/`. An earlier isolated run still failed one package validation; that result is retained in `data/evaluation/20261020T183105198046Z/`.

Every regression case therefore has a successful execution, but this is **not a claim that the original full run passed 67/67**. Code execution remains sensitive to process startup and machine load under the inherited five-second limit. No test assertion or execution limit was weakened.

Browser tests use Chrome and synthetic sources behind an explicitly offline fixture server. They cover landing/mobile layout, adaptive learning and refresh, actual generated coding package plus local Monaco and hints, seven-paper selection and persistence, inline multi-step continuation, actual PDF extraction and Word download, and persistent contextual clarification. API tests additionally cover process restart, evaluated shared-CACM changes, genuine cross-agent conflicts and diagnostic resolution, interrupted-assessment resume, duplicates, stale revisions, corrupted files, provider failures, source provenance and answer/credential redaction. Provider fixtures are never production responses.

## Screenshots and manual testing

- `data/web-e2e/screenshots/real-application.png`: actual production onboarding, no provider credentials or student data.
- `data/web-e2e/screenshots/home.png`, `learning.png`, `coding.png`, `research.png`, `mobile.png`: real React browser renders using isolated offline fixtures.

See `docs/WEB_SETUP.md` for startup, provider configuration and exact manual testing steps. Create your own profile and add your own keys to this folder's `.env` to verify paid live provider behavior. No original secrets were copied and no paid live calls were executed during implementation.

## Limitations

- Live Gemini, YouTube and academic provider behavior with your own credentials has not been validated. Offline provider fixtures verify integration, not external availability or model quality.
- Local UUID profiles are continuity, not authentication or authorization. Run locally with one backend worker. This is not a production multi-user deployment.
- The inherited Python runner has timeouts but is not a hostile-code sandbox. Use trusted code. Machine load can cause valid code/package validation to time out.
- npm audit recorded **two low-severity advisories**, associated with Monaco's DOMPurify dependency; zero moderate/high/critical advisories in that recorded audit. The initial moderate advisories were removed by upgrading Monaco. Details: `frontend/audit-results.json`. No forced downgrade or unreviewed audit fix was applied.
- Monaco's lazy-loaded editor bundle is large. Initial editor load is heavier than the main workspace.
- A Starlette/httpx test-client deprecation warning remains; tests pass.
- PDF OCR is unavailable. Analysis covers extracted selected chunks only. Field-grouped synthesis does not establish scientific consensus; proposed gaps and directions require independent review.
- Mastery remains the original rule-based, uncalibrated estimate. No real-student study establishes learning gains or mastery calibration.
- Coding drafts require Save draft before refresh. Unsubmitted text answers are not promised as saved work.
- No hosting, production authentication, secure container execution or paid live verification is claimed.

Implementation has stopped after this refinement of the independent web application. The real server is left on loopback port 8000; the fixture server is managed by the browser tests and is not the normal application.
