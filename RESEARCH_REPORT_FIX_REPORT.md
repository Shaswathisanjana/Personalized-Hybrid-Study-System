# Research report correction

The supplied Downloads/research-report.docx contained three abstract-only papers, each with 0/1 chunks analyzed. The previous export path allowed this unprocessed collection to be presented as an analysis report. It had references and coverage notes, but no evidence-based analysis body.

## Changes

- Added an explicit Prepare next report batch action. It extracts selected PDFs and analyzes a bounded batch of selected source chunks through the existing collection service. Each batch preserves successful work for retries and refresh recovery. It does not update CACM mastery.
- Show analyzed/available chunks, selected-source counts, supported claims and report readiness. Full analysis exports require completed processing and supported claims. A student can explicitly request a labelled partial report when some supported analysis exists, or download an honestly labelled references-only bibliography.
- Word and Markdown share one report structure with all twelve selectable sections, readable references, source coverage and methodology tables, actual attributed excerpts, page/chunk citations, explicit missing-field explanations and separate system-generated suggestions.
- Preserve abstract-only versus full-text excerpt scope. Do not invent datasets, results, methodologies or citations. Export does not call the AI provider.
- Default new report selections include all sections. Existing saved section choices remain respected; Select all report sections is available.

## Exact source files changed in PHSS_Web_App

Modified:
- backend/main.py
- backend/service.py
- app/research_agent/collection_service.py
- frontend/src/App.tsx
- frontend/e2e/workspace.spec.ts

Created:
- backend/research_reports.py
- backend/tests/test_research_report_flow.py
- RESEARCH_REPORT_FIX_REPORT.md

Updated the existing WEB_FILES_CHANGED.json inventory and rebuilt generated frontend/dist assets. Test outputs and screenshots are in data/web-e2e and data/evaluation. Pre-edit backups are under data/source_backups/research_report_fix_20261022. No original PHSS_Git source files were modified; all 318 files in COPY_VERIFICATION.json matched their original hashes after the work. The supplied downloaded Word file was read, not overwritten.

## Executed checks

- npm.cmd --prefix frontend run build: passed TypeScript checking and production build. Existing large-bundle warning remains.
- .venv/Scripts/python.exe -B -m pytest backend/tests -q -p no:cacheprovider: final run 35 passed, 1 Starlette deprecation warning, 116.05 seconds. An initial run had 34 passed and 1 failure in the new test's upload-response assertion; the assertion was corrected and the entire suite rerun successfully.
- npx.cmd playwright test (frontend): 9 passed, 28.3 seconds, Chrome. Includes actual report readiness gating, three-paper preparation, valid Word download and refresh recovery, plus the existing learning, coding, research and clarification scenarios.
- tools/evaluate_offline.py --only test_research_docx_export: 7 tests passed.
- tools/evaluate_offline.py --only test_research_pdf_collection: 9 tests passed.
- tools/evaluate_offline.py --only test_research_full_text_analysis: 4 tests passed.
- tools/evaluate_offline.py --only test_research_search_collection: 13 tests passed.
- Opened browser-generated DOCX files with python-docx: prepared abstract report has 111 paragraphs and 2 tables; PDF report has 70 paragraphs and 2 tables. Fixtures are synthetic and are not research publications.
- Restarted only the verified new-app servers on ports 8000 and 8001. Both landing pages return 200 and both expose the new prepare-report POST endpoint.

## Manual verification

1. Open the existing web app URL (http://127.0.0.1:8000 or http://127.0.0.1:8001) and press Ctrl+F5.
2. Open the research activity and select the papers/PDFs to include.
3. In the report area click Prepare next report batch. Repeat until readiness reports the selected sources are analyzed. Read any extraction/provider errors; retry or deselect unusable sources.
4. Click Select all report sections, set the title/topic and click Generate Word report. Markdown remains available.
5. Inspect individual paper sections, methodology comparison, source coverage, references and citations. An abstract-only source can support only what its abstract states. Upload the full paper PDF for more coverage.
6. Refresh and confirm the collection and readiness recover. Research processing and export should not change mastery.

## Limitations

No paid/live provider analysis of the student's actual PCB papers was run as part of testing. The supplied old report is not retroactively rewritten: regenerate it after preparing the selected sources. Report richness depends on extractable source content and the existing grounded analyzer. Unavailable objectives/datasets/findings are explicitly marked; abstract-only reports may remain sparse. Synthesis groups supported evidence by field and distinguishes matching/distinct descriptions; it does not establish scientific consensus or prove novel research gaps. Scanned PDFs still require usable text/OCR outside the existing extractor. Processing retains the existing configured limits and may require multiple explicit batches. The report button's displayed default batch sizes are the existing configuration (3 PDFs/6 chunks). Browser evidence is data/web-e2e/screenshots/research-report-ready.png. No commits or pushes were made.
