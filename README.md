# PHSS Web App

Independent React + TypeScript + Vite + Tailwind / Radix UI frontend with FastAPI adapters around the existing Python agents, autonomous orchestrator and shared CACM.

## Run

From this folder:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open http://127.0.0.1:8000 . The built React frontend is served by FastAPI. Add your own provider keys to this project's .env to enable live content; no original secrets or student data are included.

[Setup and manual checks](docs/WEB_SETUP.md) | [Web delivery report](WEB_APP_COMPLETION_REPORT.md) | [Copied architecture](docs/ARCHITECTURE.md)

The original PHSS_Git checkout and environment are separate. Never share writable databases between them. This app uses data/student_state/phss.sqlite3 inside this folder.

## Verify

```powershell
.\.venv\Scripts\python.exe -B -m pytest backend/tests -q
.\.venv\Scripts\python.exe -B tools/evaluate_offline.py
npm.cmd --prefix frontend run build
```

From frontend/: `npx.cmd playwright test` runs Chrome against an explicitly isolated offline fixture server. Browser fixture content is synthetic and never used by the production launcher.

Local profiles are not authenticated accounts. The inherited local Python runner is not a hostile-code sandbox. Mastery is rule-based, without real-student calibration. Historical milestone reports describe the copied Streamlit application; the web delivery report describes this independent application's implementation and verification.

The original README is preserved at docs/LEGACY_STREAMLIT_README.md. The retained Streamlit application can still run separately using run_phss.py; it is not the web frontend.
