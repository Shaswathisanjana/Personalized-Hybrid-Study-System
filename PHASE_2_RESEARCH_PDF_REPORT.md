# Phase 2 — Research PDF Collection and Analysis

Implemented on 20 October 2026. Scope is Phase 2 only. Academic search collection selection, DOCX export, open-topic coding and unified autonomous orchestration were not implemented.

## Existing code preserved and reused

The existing abstract research workflow, provider architecture, comprehension assessment, Learning/Coding agents and CACM algorithms remain intact. The PDF path uses the existing summarizer's provider/client conventions, `PaperSummary`, `MethodologyComparator`, `ResearchGapIdentifier` and `ResearchObjectiveGenerator` through an explicit PDF-excerpt adapter. It does not place full text in an abstract field or claim full-text analysis from metadata.

The PDF UI sits above the original abstract form. The original form, recovery job, diagnostic and assessment workflows, five-paper search slider and abstract Markdown export are retained. Uploaded PDFs have their own configurable stored-document limit (100 by default), not that slider's five-paper cap.

## Exact files

| Status | File | Purpose |
| --- | --- | --- |
| Created | `app/research_agent/collection_models.py` | Validated configurable collection/processing limits and analysis fields |
| Created | `app/persistence/research_document_store.py` | Owner-scoped PDF bytes, durable JSON results, selection, deduplication and document revisions |
| Created | `app/research_agent/pdf_extractor.py` | Disposable subprocess orchestration and extraction timeout handling |
| Created | `app/research_agent/pdf_extractor_worker.py` | Actual PDF metadata/text extraction with page/chunk identities and rejection statuses |
| Created | `app/research_agent/pdf_worker_limits.py` | Windows Job Object / POSIX address-space worker memory limit |
| Created | `app/research_agent/full_text_analysis.py` | Bounded provider requests, exact quotation validation and PDF-backed comparison adapter |
| Created | `app/research_agent/collection_service.py` | Explicit bounded extraction/analysis batches and persisted partial failure recovery |
| Created | `app/research_agent/streamlit_collection.py` | Multi-upload, selection/removal, extraction inspection, page-cited results and collection comparison UI |
| Created | `pdf_collection_test_fixtures.py` | Locally generated, explicitly synthetic PDF bytes and offline analysis fixtures |
| Created | `test_research_pdf_collection.py` | Nine real-PDF extraction, ownership, limits, schema migration, backup and retry tests |
| Created | `test_research_full_text_analysis.py` | Four provider-boundary, grounding, request configuration and timeout tests |
| Created | `test_research_collection_streamlit.py` | Two actual main-app upload/analysis/recovery/profile tests with real fixture bytes |
| Created | `docs/RESEARCH_PDF_COLLECTION.md` | Manual workflow, configuration, provenance, storage and limitations |
| Created | `PHASE_2_RESEARCH_PDF_REPORT.md` | This report |
| Modified | `app/persistence/sqlite_store.py` | Additive schema 3-to-4 migration adding the PDF table; preserve existing snapshots/backups |
| Modified | `app/research_agent/streamlit_page.py` | Embed dedicated PDF section and distinguish its scope from the original abstract form |
| Modified | `requirements.txt` | Pin the approved `pypdf==6.21.1` dependency |
| Modified | `tools/local_environment.py` | Check the now-required PDF parser alongside existing dependencies |
| Modified | `tools/offline_suite.json` | Include the three Phase 2 test modules in the maintained suite |
| Modified | `README.md` | Describe PDF functionality and updated evaluation scope |
| Modified | `docs/SETUP.md` | Document approved dependency addition and collection setup |
| Modified | `docs/EVALUATION.md` | Describe the expanded 18-module suite |

Affected existing files were backed up before editing in `.milestone_backups/phase2_pdf_20261020/`. Protected/unrelated modifications were preserved. The active IDE file, `app/research_agent/report_exporter.py`, was not changed in this phase.

## Features and guarantees verified offline

- **More than five PDFs:** a seven-document collection uses real, generated PDFs with page text. Extraction defaults to three documents per action and analysis to six page chunks per action; these are batch sizes, not collection caps.
- **Actual content:** every model request contains extracted page text. Accepted findings are exact, bounded quotations, with a document SHA-256, page and chunk ID; extracted chunks also retain character offsets. Findings are not inferred from filenames or generated rewrites.
- **Unknown metadata:** only supplied PDF title/author values are reported. Missing title, year and publication details remain unknown. File names are explicitly display labels.
- **Graceful failures:** invalid headers, corrupt PDFs, encrypted documents, scanned/text-poor files, page/text/file/count/byte limits and worker timeouts have explicit outcomes. OCR is unavailable and is never implied.
- **Durability/isolation:** original bytes and derived results live in the existing SQLite database, keyed by student and hash. Reopening, refresh and profile switching preserve the correct collection. Existing SQLite backups include the document table.
- **Recovery:** each successful document/chunk is checkpointed. Failed chunks remain retryable; completed chunks are not repeated. New unfinished chunks are prioritized ahead of failed retries. Stale writes and results for removed documents are rejected.
- **Removal:** an explicit action removes only the selected owner's document from the active collection. Original bytes/results are retained for recovery and still count toward quotas; re-upload reactivates the same hash. Clearing study progress does not erase PDFs.
- **Collection analysis:** per-document fields, an existing-service methodology comparison, attributed field-based evidence themes, matching/distinct wording, limitation-derived preliminary opportunities and labelled system-generated objectives.
- **No mastery side effects:** the final UI scenario starts with assessed learning/coding evidence and a genuine conflict, then uploads/extracts/analyzes seven PDFs and refreshes. Concepts/mastery/attempts, evidence and the real conflict remain unchanged.

## Dependency installation

With explicit user authorization, ran:

```powershell
python -m pip install --no-deps --target .venv/Lib/site-packages pypdf
```

The sandboxed attempt was network-blocked; the same command completed after escalation. Installed `pypdf 6.21.1` (approximately 405 kB wheel). No environment was recreated, pip upgraded, or other dependency installed/upgraded. Existing Streamlit 1.64.0, google-genai 2.24.0 and python-dotenv 1.2.3 versions remain unchanged. `.env` was not edited and no credentials were printed.

## Executed verification

```powershell
python -B tools/evaluate_offline.py
python -B tools/evaluate_offline.py --only test_research_collection_streamlit
python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline
python -B run_phss.py --check
git diff --check -- app/persistence/sqlite_store.py app/research_agent/streamlit_page.py tools/local_environment.py tools/offline_suite.json requirements.txt README.md docs/SETUP.md docs/EVALUATION.md
```

Also ran focused Python `unittest` commands for the new modules and existing `test_research_analysis_streamlit`, using the process-local `.venv/Lib/site-packages` fallback.

The expanded full suite passed **59/59 cases: 135 application unittest executions and 41 standalone regression scripts**, with zero failures, errors, skips or timeouts. This includes the previous 120 application tests and 15 new PDF tests. Full results/logs are in `data/evaluation/20261020T101557028473Z/`.

Infrastructure checks additionally passed **13/13**; dependency imports passed; syntax parsing passed **316 Python files**; README/docs local links resolved. After the final evidence-theme UI update and stronger pre-existing-CACM assertions, the focused PDF UI run passed **2/2**, with results in `data/evaluation/20261020T102134510608Z/`. Focused runs are not added again to the 135 distinct application test count.

Initial new tests exposed fixture/import assumptions: an already-stored identical file was correctly treated as a duplicate rather than a new byte-quota violation; PDF metadata titles correctly took precedence over filenames; a new test initially referenced the wrong existing helper class name. These new tests were corrected without changing existing regression assertions. Earlier failed runs were not counted as passes.

Protected SHA-256 values remain:

- `test_evidence_store.py`: `FC39C8DF1623202AC1570A5288B2823613D3E1200DD1761D25FCFFDCF113035C`
- `test_misconception_analyzer.py`: `6B0A9C6A75EA74F20F0EAFB5810188FBB18417429D2470D934A513D75BE07F68`

## Limits and unverified behavior

The analysis is intentionally extractive. Exact quotation checking verifies text membership, not perfect semantic classification or a paper's scientific validity. Evidence themes organize source excerpts and matching wording; they are not a free-form semantic literature-review narrative. Comparison cells use the first supported excerpt per field; individual analysis retains all excerpts. Page/image gaps and incomplete chunk analysis are labelled. No exhaustive literature search or real-student learning improvement is claimed.

PDF metadata often lacks publication details; this phase leaves them unknown rather than inferring from dates, titles or filenames. No OCR, password handling, PDF-specific comprehension quiz, PDF report download or DOCX export was added. Existing abstract assessment and Markdown export still work with their original scope. Search-selection/DOCX are Phase 3 work.

Streamlit buffers chosen uploads in the main process; per-worker memory ceilings do not cap whole-server memory or provide filesystem/network security. This remains a trusted local prototype. Windows worker limits were exercised here; POSIX resource limiting was not tested on this Windows machine. Failed provider responses lost before a checkpoint may require another call; exactly-once billing is not promised.

No real PDF collection or live Gemini analysis was used during verification. AppTest supplies real PDF fixture bytes at the native upload boundary; browser file-picker behavior and real-provider quality/costs require manual validation. Real student databases were not used by the tests. Application schema migration occurs when an existing database is opened by the updated application.

## Manual verification and stopping point

Follow `docs/RESEARCH_PDF_COLLECTION.md`: select a saved profile, open Advanced Research Agent, add seven or more text PDFs within the displayed limits, extract successive batches, inspect text, explicitly analyze successive batches, and inspect quotes/comparison. Refresh/restart and revisit the same profile, switch to another profile, retry a failed chunk and remove one paper from the active collection. Confirm original assessed progress stays unchanged. Analysis sends selected text to the configured provider and may incur charges; extraction is local.

Stop after Phase 2. No Phases 3–6, commits, staging or pushes were performed.
