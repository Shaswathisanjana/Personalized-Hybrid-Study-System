# Local setup

Run commands from the repository root. The verified workspace is Windows with Python 3.12. The existing `.venv/Lib/site-packages` contains Streamlit 1.64.0, google-genai 2.24.0 and python-dotenv 1.2.3. These are observed installed versions, not a fresh-install guarantee. No packages were installed or upgraded during milestone verification.

The Python application imports `streamlit`, `google.genai`, `dotenv`, `pypdf` and `docx`. `requirements.txt` records observed versions, including the DOCX dependency `lxml`. It is not a transitive lock file, and a clean installation has not been validated. The approved additions were `pypdf==6.21.1` in Phase 2 and `python-docx==1.2.0` plus its required `lxml==6.1.3` in Phase 3. They were installed into the existing `.venv/Lib/site-packages` directory without recreating the environment or upgrading existing packages. See [PDF collection limits](RESEARCH_PDF_COLLECTION.md) and [topic search/Word reports](RESEARCH_SEARCH_AND_DOCX.md).

## Start

```powershell
python -B run_phss.py --check
python -B run_phss.py
```

The check command imports dependencies without opening student storage or calling providers. The launcher uses the current interpreter, appends the existing Windows package directory if present, binds to `127.0.0.1`, disables usage telemetry and stays in the foreground. Stop it with Ctrl+C. Use `--port 8502` if the default port is already occupied. It does not provide authentication or secure code execution.

In this checkout `.venv/Scripts/python.exe` is absent, although packages are present. The launcher handles that case. The equivalent manual fallback is:

```powershell
python -B -c "import sys,runpy; sys.path.append('.venv/Lib/site-packages'); sys.argv=['streamlit','run','review_ui.py']; runpy.run_module('streamlit',run_name='__main__')"
```

In a complete environment, `python -m streamlit run review_ui.py --server.address=127.0.0.1` also works. The evaluation runner appends the local Windows package directory when present. Neither command repairs the environment.

For a separate clean environment, the intended installation command is `python -m pip install -r requirements.txt` inside that environment. Installation/downloads have not been performed or verified and require approval; do not run this against the existing environment by accident.

## Providers

Live features require `GEMINI_API_KEY`; YouTube retrieval uses `YOUTUBE_API_KEY`. Supply keys privately through the process environment or the existing ignored `.env` mechanism. Do not put secrets in source, screenshots or artifacts. OpenAlex and Wikipedia retrieval require network availability. Quotas, model availability and generated-answer quality can change.

Live Generate/Submit actions may incur charges. Offline evaluation uses fixtures, dummy process-local keys and an external TCP connection guard. It does not validate real credentials or live services.

## Student data

The app creates `data/student_state/phss.sqlite3`. Keep the `student` URL identifier to reopen the same profile. Use profile controls deliberately; a new profile begins independently. Ordinary activity restart preserves history; explicit clear requires confirmation and removes the selected student's active state.

Create a consistent backup with SQLite's online backup API:

```powershell
python -B tools/backup_student_data.py
```

The default writes a new timestamped file under ignored `data/student_state/backups/`. It opens the source read-only, includes committed WAL data, checks backup integrity and refuses to overwrite any destination. `--source` and `--destination` select explicit paths. A failed backup may leave an incomplete destination; it is never presented as successful. No real student backup was created during automated verification.

For restoration, stop all app processes first, retain the current database and its WAL/SHM companion files together as a separate recovery copy, then restore a verified backup to the expected path. Do not restore over an active database or leave old companion files beside a restored database. Test restoration with disposable data before using it on student records. Keep backups private: answers, code and research activity may be stored. Persistent writable storage is required across server restarts.

## Local delivery checks

```powershell
python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline
python -B tools/smoke_startup.py
```

The startup check launches its own server on a temporary loopback port, requests only the HTTP health endpoint and stops that server afterward. It does not open a browser, run a student session or validate live providers. Backup tests use disposable databases and verify WAL contents, source preservation and overwrite rejection.

`server.js` and MongoDB are not needed by `review_ui.py`. Do not run old root-level `fix_*`, `integrate_*` or `repair_*` scripts as setup commands; they are historical code-editing helpers.
