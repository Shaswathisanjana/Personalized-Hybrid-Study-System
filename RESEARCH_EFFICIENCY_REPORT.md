# Research reliability and report-quality refinement

## Diagnosis from the supplied report

The supplied research-report (1).docx contains six abstract-only papers, with only two of six chunks analyzed. Three sources failed with provider 503 errors and one failed quote validation. The student explicitly downloaded a partial report. Missing-paper notices were repeated in every analysis section, and raw provider diagnostics appeared in the exported document.

## Implemented

- At most two source-analysis attempts within the existing per-chunk time budget. Retry transient 408/429/500/502/503/504 responses and connection/timeouts; do not retry authentication/configuration errors. Individual SDK requests have automatic retries disabled to avoid multiplying attempts.
- Retry invalid JSON/unsupported quotations once with a precise source-only repair instruction.
- Recover whitespace-only differences by locating and storing the exact original continuous source span. No fuzzy matching or paraphrase acceptance.
- If a second response contains valid fields alongside invalid ones, keep only individually validated fields and persist an explicit warning naming omitted fields. Completely unsupported responses remain failures. No invented facts are accepted to fill report sections.
- Clarified extraction instructions: generic mentions of datasets/assessment indices are not named datasets/metrics, and proposed future methods must be distinguished from methods used.
- Existing successful chunk analyses remain cached. Preparation retries unfinished chunks; it does not re-analyze successful chunks or change mastery.
- Partial reports retain all selected sources in coverage/references, but exclude wholly unanalyzed papers from individual analytical sections and methodology comparisons.
- Replace raw provider exception payloads in exports with readable recovery explanations. Detailed errors remain in the application for diagnosis.

## Exact files changed

Modified (PHSS_Web_App only):
- app/research_agent/full_text_analysis.py
- app/research_agent/collection_service.py
- backend/research_reports.py

Created:
- backend/tests/test_research_reliability.py
- RESEARCH_EFFICIENCY_REPORT.md

The WEB_FILES_CHANGED.json inventory is updated. Source backups are retained under data/source_backups/research_efficiency_20261022 and the previous research_report_fix_20261022 folder. The supplied DOCX was not overwritten. All 318 original PHSS_Git source files in the preservation manifest were verified unchanged.

## Verification

- Final full backend run: 42 passed, 1 existing Starlette deprecation warning, 151.30 seconds. Includes seven new deterministic tests for transient recovery, repair retries, exact-span whitespace normalization, authentication handling, timeout budgets, preservation of valid fields and concise partial reports.
- Chrome Playwright: 9 passed (1.1 minutes), including real report preparation, Word download and refresh recovery.
- Existing offline research suites: full-text analysis 4/4, PDF collection 9/9, Word export 7/7, search collection 13/13. All 33 passed.
- Intermediate verification: a run before the final additional test passed 41 tests. A subsequent focused run encountered a new test-file encoding issue, corrected before the final run. A concurrent full run had 41 passed and one unrelated coding-exercise validation failure; the full suite was rerun alone and all 42 passed. No test timeout was loosened.
- Both updated local servers were restarted and their health endpoints return HTTP 200. No live student analysis or paid provider request was used for verification.
- All 318 original-source preservation hashes match.

## Use

Hard-refresh the running app on port 8000 or 8001. Open the research activity and select the papers. Click Prepare next report batch to retry remaining chunks. Existing successful analyses are retained. Continue until ready, or wait and retry later if the provider remains unavailable. Select all report sections before generating the Word report. Only enable partial export if incomplete coverage is acceptable.

## Limits

No live provider requests were made to process the student's actual papers during verification. An unavailable provider cannot be made reliably available by application code; the fixed retry budget limits cost and waiting. Multiple chunks are still processed sequentially in configured bounded batches, so a batch can take several minutes. Existing completed analyses are not retroactively reclassified by new prompts; the original source quotations and prior coverage remain visible. Fields omitted after grounding checks remain explicitly unavailable and may require a better source/full-text PDF. Abstract-only papers often lack datasets, detailed methods and reproducible evaluations. Synthesis remains evidence grouping rather than a verified scientific systematic review. A complete analysis means all selected chunks were processed, not that every desired field exists. The original Streamlit project and student files were not changed. No commit or push was made.
