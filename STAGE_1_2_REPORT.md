# PHSS Web App: stages 1 and 2

Independent source copy only. React, Vite, Tailwind, FastAPI and Monaco are NOT implemented yet. No dependencies installed, no environment or credentials copied, and no provider calls made.

## Layout
- app/: existing Python agents, CACM, orchestration and persistence, copied unchanged
- tools/: existing tooling
- tests/ and test_*.py: existing fixtures and tests
- docs/: existing documentation (historical instructions refer to Streamlit)
- review_ui.py and run_phss.py: retained legacy Streamlit entry points
- requirements.txt: existing Python dependencies only
- data/student_state/phss.sqlite3: newly initialized empty schema, no original student records
- .env.example: empty provider-key placeholders; no credentials
- COPY_VERIFICATION.json: per-file SHA-256 and source verification

No original databases, PDFs, environments, Git metadata, backups or generated reports were copied. The source is not imported by this copy. Default SQLite resolution is relative to the copied module, so it points inside this project. Future FastAPI adapters must use this application's store only.

Verification: every copied file matched its source SHA-256; all copied Python files parsed; the copied store initialized an empty database; source non-generated file hashes and Git status were unchanged. No regression suites or browser tests were executed during duplication. Dependency installation, independent server startup and full workflow validation remain for later approved stages. No API or frontend exists yet.

Stop here pending approval for stage 3. Do not treat historical completion reports as completion of this new web application.
