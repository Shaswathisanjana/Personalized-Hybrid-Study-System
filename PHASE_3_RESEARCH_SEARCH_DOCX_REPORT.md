# Phase 3 — Academic Topic Search and DOCX Research Report Export

Implemented on 20 October 2026, extending Phase 2. Phases 4, 5 and 6 were not implemented. No commits, staging, pushes, resets, cleans or discards occurred.

## Functionality

**Search Research Papers by Topic** is visible on the existing Advanced Research Agent page. Arbitrary topics use the existing AcademicPaperSearch/OpenAlex provider layer, with bounded cursor retrieval, saved search results, title/author filtering, usable-abstract filtering and display pagination. Actual supplied titles, authors, year, abstracts, DOI and source URLs are shown. Missing fields and rejected abstracts remain explicit. Default targets extend to 1000, with configurable bounds; the old abstract-analysis slider also accepts more than five within its existing backend ceiling of 100.

Each retrieval action fetches one bounded page. Successful pages, individual checkbox selections, cursors and errors persist in SQLite. Failed pages retain earlier results/selections and can be retried. Targets are not guaranteed: duplicates, rejected/missing abstracts, provider exhaustion, credentials, quotas and resource bounds can cause shortfalls. Duplicate provider IDs, DOI and conservative source identities do not create duplicate academic collection entries. A newly usable abstract can upgrade an excluded metadata-only entry without fabricating text.

Selected results enter a persistent academic collection alongside the original PDF collection. One analysis service processes both source types in bounded chunks, retaining `abstract_only` versus `full_text_excerpts` and PDF page/chunk identifiers. Abstract chunks have no invented page number. Existing comparison, gap and objective services are reused through the source adapter. Successes survive partial failures; removed/stale records reject late writes. Searching, uploading, selection, analysis and export do not call the cognitive evidence-update APIs.

**Generate Research Report (.docx)** creates a real Word package locally with selectable source papers and twelve section controls. It uses only available selected analysis. Headings, a methodology table, references, safe HTTP(S) hyperlinks, page breaks, scope notices and source citations are included where applicable. Unavailable analysis sections are omitted. Original paper objectives remain separate from system-generated directions. Gaps/directions reuse the existing limitation-grounded services and are explicitly proposals, not paper findings or verified novelty claims.

Report title/topic, selected sources and sections persist per profile. Existing saved abstract analyses are also available to Word export after rerun/refresh; their observations and checked source quotations are reused without another generation call. Existing Markdown export remains unchanged in the original abstract workflow. Download bytes can be regenerated without repeating analysis.

## Exact files created

| File | Purpose |
| --- | --- |
| `app/research_agent/search_session.py` | Configurable, persisted incremental search and individual selection |
| `app/persistence/research_library_store.py` | Owned academic-source records and a unified PDF/abstract document adapter |
| `app/research_agent/research_report.py` | Validated mixed-source report view and existing saved-analysis adapter |
| `app/research_agent/docx_exporter.py` | Actual selectable Word export, provenance, tables and hyperlinks |
| `app/research_agent/streamlit_search.py` | Topic search, filters, page loading, selection and collection addition |
| `app/research_agent/streamlit_library.py` | Mixed analysis, collection inspection and persistent Word report controls |
| `test_research_search_collection.py` | 13 parsing, search, identity, ownership, recovery and key-transport checks |
| `test_research_docx_export.py` | Seven package/content/section/provenance/legacy-export checks |
| `test_research_search_streamlit.py` | Three actual main-app search, retry, analysis, report and profile checks |
| `tests/fixtures/openalex_work_projection.json` | Four actual OpenAlex bibliographic response fields; omitted fields are not invented |
| `tests/fixtures/README.md` | Fixture provenance and distinction from synthetic pagination/analysis fixtures |
| `docs/RESEARCH_SEARCH_AND_DOCX.md` | Manual workflow, provider setup, limits and verification boundaries |
| `PHASE_3_RESEARCH_SEARCH_DOCX_REPORT.md` | This report |

## Exact existing files modified

| File | Change |
| --- | --- |
| `app/persistence/sqlite_store.py` | Additive schema 4-to-5 migration for search sessions, academic sources and report preferences |
| `app/persistence/state_codec.py` | Explicit legacy default for the new ResearchPaper DOI field |
| `app/research_agent/models.py` | Optional DOI metadata, preserving existing constructors |
| `app/research_agent/providers/openalex.py` | Cursor page retrieval, DOI parsing, response bounds and optional private authorization header |
| `app/research_agent/paper_search.py` | Incremental method through the existing provider abstraction |
| `app/research_agent/source_identity.py` | DOI identity matching and pre-DOI empty-field cache-key compatibility |
| `app/research_agent/collection_service.py` | Optional unified document-store injection; preserve original PDF behavior |
| `app/research_agent/full_text_analysis.py` | Scope-aware abstract/PDF prompts, provenance and mixed comparison scope |
| `app/research_agent/streamlit_page.py` | Embed new interfaces and remove the old five-paper slider maximum |
| `requirements.txt` | Approved python-docx and required lxml version pins |
| `tools/local_environment.py` | DOCX import preflight |
| `tools/offline_suite.json` | Add the three Phase 3 modules |
| `README.md` | Current research capabilities, report guide and suite scope |
| `docs/SETUP.md` | Dependency additions and new guide |
| `docs/EVALUATION.md` | Expanded 21-module suite |
| `docs/RESEARCH_PDF_COLLECTION.md` | Link to Phase 3 while retaining the Phase 2 instructions |

Existing files were backed up before edits under `.milestone_backups/phase3_search_docx_20261020/`, preserving their relative paths. The original Markdown exporter, Learning/Coding agents, cognitive algorithms, assessed-response boundaries and unrelated modifications were not rewritten.

## Dependency installation and provider configuration

Installed only the approved `python-docx==1.2.0` and its required `lxml==6.1.3` dependency into the existing `.venv/Lib/site-packages` directory:

```powershell
python -m pip install --no-deps --target .venv/Lib/site-packages python-docx lxml
```

The initial sandboxed attempt was network-blocked; the installation succeeded after escalation. No environment was recreated, pip upgraded or existing package upgraded. Observed Streamlit 1.64.0, google-genai 2.24.0, python-dotenv 1.2.3 and pypdf 6.21.1 remain unchanged. `.env` was not edited and no credential values were printed.

OpenAlex pagination/authentication were checked against its official [paging](https://help.openalex.org/api/paging/) and [authentication](https://help.openalex.org/api/authentication/) documentation. Optional `OPENALEX_API_KEY` is sent in a bearer header, never added to source URLs or saved search data. Cursor paging beyond the first page requires provider authorization under the documented policy. HTTP failures remain visible; no account/email/key-creation action was performed.

A public OpenAlex work response was inspected to produce the explicitly documented four-field bibliographic fixture. This is not a live application search/quality benchmark. All executed application tests use offline fixtures and temporary student databases; no live Gemini request was made.

## Actual verification

```powershell
python -B tools/evaluate_offline.py
python -B tools/evaluate_offline.py --only test_research_search_collection
python -B tools/evaluate_offline.py --only test_research_docx_export
python -B tools/evaluate_offline.py --only test_research_search_streamlit
python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline
python -B run_phss.py --check
```

Also executed focused unittest commands with the existing package fallback for new DOCX/search modules and existing research recovery, full-text and Streamlit modules. The original focused 25-test recovery/full-text/legacy-UI run passed; later saved-analysis export/legacy-UI verification passed 15 tests. No existing regression assertions were weakened.

The full curated run passed **62/62 cases: 157 application test executions and 41 standalone regression scripts**, with zero failures, errors, skips or timeouts. Artifacts: `data/evaluation/20261020T105632794012Z/`.

After that run's search module had executed, one key-transport test was added. Final focused runs passed **13 search/collection tests**, **7 DOCX tests** and **3 search/UI tests**, including that additional test and the saved-analysis export adapter. This gives **158 distinct application checks passed across the full and focused runs**, not 158 executions in the recorded full run. The full run's test count is retained honestly rather than rewritten. Final focused artifact paths are recorded below.

| Final focused module | Tests | Artifact directory |
| --- | ---: | --- |
| `test_research_search_collection` | 13 | `data/evaluation/20261020T110457535800Z/` |
| `test_research_docx_export` | 7 | `data/evaluation/20261020T110818633376Z/` |
| `test_research_search_streamlit` | 3 | `data/evaluation/20261020T111015601436Z/` |

The final UI check also verifies that lowering the configured maximum target to one remains usable even when a larger saved target exists. The final Word check includes mandatory per-source coverage counts even when optional limitations/reference sections are unchecked.

Tooling checks passed **13/13**. Dependency preflight passed. Syntax parsing passed **325 Python files**, local README/docs links resolved, and scoped whitespace checks passed. Protected hashes remain unchanged:

- `test_evidence_store.py`: `FC39C8DF1623202AC1570A5288B2823613D3E1200DD1761D25FCFFDCF113035C`
- `test_misconception_analyzer.py`: `6B0A9C6A75EA74F20F0EAFB5810188FBB18417429D2470D934A513D75BE07F68`

The main-app scenario searches an arbitrary topic, persists seven selected papers, analyzes them in bounded batches, selects two sources and specific Word sections, generates the download, restores report preferences, switches student profiles and verifies unchanged pre-existing mastery/evidence. Separate tests cover corrupted responses, missing metadata, duplicate records, failed retrieval/analysis recovery, PDF page citations versus abstract identifiers, genuine Word package readback, XML sanitation, hyperlinks and unchanged Markdown availability.

## Limitations and manual verification

Follow `docs/RESEARCH_SEARCH_AND_DOCX.md`. Open Advanced Research Agent, search a topic with a target above five, load additional pages, select papers and add them to the collection. Extract any uploaded PDFs, analyze mixed batches, select Word sources/sections, generate/download the report, refresh and switch profiles. Existing saved abstract analyses appear in the Word form on a subsequent rerun. Verify references and scope labels in your Word viewer. Retrieval needs provider access/quotas; Gemini analysis sends selected text externally and may incur charges. DOCX generation itself is local.

Native browser picker/download interaction, Microsoft Word desktop rendering, real-provider credential validity, live search relevance and live Gemini analysis quality were not tested. DOCX structure and contents were read back with python-docx. OCR remains unavailable. Field-based thematic synthesis and quotation wording comparisons do not establish scientific consensus, systematic-review completeness or actual contradictions. Missing analysis is omitted; proposals are explicitly tentative system suggestions. Large reports may be long and use main-process memory; configurable source bounds are not a server security sandbox. Existing local-profile and code-execution security limits remain unchanged.

Phase 3 stops here for user approval. Phases 4–6, commits and pushes remain unstarted.
