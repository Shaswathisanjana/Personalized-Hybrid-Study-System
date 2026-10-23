# Grounded report-writing implementation

## Problem addressed

The latest supplied research-report (3).docx contains all sections and eight analyzed abstracts, but its field-list exporter does not connect evidence into a readable account. Existing analysis places an explicit HRIPCB dataset description under objectives, misses evaluation descriptions already present in findings, and includes a future-work model quotation as model evidence. Processing completion is not scientific verification.

## Implementation

New backend/report_synthesis.py provides a pure report-only evidence repair and extractive writing layer:

- Reuse a saved exact quotation in the dataset field when it explicitly contains a dataset reference and quantitative image/sample/class information. This recovers the HRIPCB sentence without inventing a dataset or changing student records.
- Reuse explicit numeric metric quotations from other fields as evaluation evidence. Do not compute new metrics or infer evaluation protocols.
- Exclude generic assessment-index mentions from metric evidence and generic widely-used-dataset mentions without quantitative detail from the dataset field.
- Exclude explicit future-work model references from model evidence and generic statements that future directions exist from limitation anchors.
- Every retained/reused quotation preserves its source identity, page and chunk. Source records and successful analyses are not overwritten.
- Compose individual overviews and thematic/cross-paper sections as connected, attributed prose with exact source quotations and neutral connectors. Split long cross-paper narratives into short paragraphs. The prose does not claim scientific consensus, causation, method superiority or common benchmark conditions.

backend/research_reports.py applies this layer consistently to both Word and Markdown. Existing bibliography, source coverage, references, comparison tables, section choices, partial-export gating and source limitations are retained. Report-only repairs use saved evidence and require no paid provider request. Existing strict quotation validation remains the trust boundary.

The extraction prompt in app/research_agent/full_text_analysis.py now explicitly permits one source quotation to support multiple fields, asks for dataset counts in the dataset field and named metrics from findings in evaluation, and excludes generic future-work statements from limitations. New analyses benefit from the prompt; old analyses are preserved and improved in the report view.

## Exact files

Modified:
- backend/research_reports.py
- app/research_agent/full_text_analysis.py
- backend/tests/test_report_truthfulness.py (assert the stricter future-work exclusion instead of expecting it to appear with a caveat)

Created:
- backend/report_synthesis.py
- backend/tests/test_report_synthesis.py
- GROUNDED_REPORT_WRITING_REPORT.md

Updated inventory: WEB_FILES_CHANGED.json. Backups: data/source_backups/report_synthesis_20261022. No environment recreation, package installation, commits or pushes.

## Verification

- Complete backend regression suite: 52 passed, one existing Starlette deprecation warning, 136.76 seconds. The previously intermittent coding validation test also passed in this run.
- Existing offline test_research_docx_export: 7 passed; test_research_full_text_analysis: 4 passed.
- Chrome browser checks: 2 passed, 23.0 seconds, covering PDF extraction/analysis, Word download, research report preparation and refresh recovery.
- Opened both browser-produced DOCX files with python-docx: both valid, each with two tables and the new narrative overview. Fixtures are synthetic, not real publications.
- Evidence-repair tests cover the HRIPCB-style 1,386-image/six-defect dataset sentence, metric recovery from findings, source immutability, provenance retention, future-work exclusion, no fabrication from generic mentions, narrative attribution and idempotent claims.
- Earlier checks found assertions expecting the old generic/future-work excerpts to remain. Those assertions now require exclusion; the final complete suite passed with no tests skipped.
- All 318 original PHSS_Git files in COPY_VERIFICATION.json match their preservation hashes. The supplied Word document was not overwritten.
- Restarted only verified PHSS_Web_App servers on ports 8000 and 8001; both return HTTP 200 health. No live provider call or paid student-paper analysis was executed during verification.

## Manual use

Refresh the running web application on port 8000 or 8001. Open research, select the desired sources, click Select all report sections and generate Word or Markdown. Already saved analyses do not need another provider call to benefit from report-only repair and writing. Upload readable full-text PDFs and explicitly prepare them if more detailed methods or evaluation evidence is needed. Confirm that the HRIPCB dataset sentence, when present among saved quotations, now appears in dataset information with its original attribution.

## Practical limits

This is conservative extractive synthesis, not unrestricted AI paraphrasing or an independently verified systematic review. Paragraphs retain exact quotations because arbitrary newly generated factual prose would require a stronger semantic verification system and still could not guarantee zero hallucinations. Field repair uses narrow lexical rules, not a claim of full semantic understanding, and can miss dataset descriptions that do not match those explicit cues. It does not manufacture absent fields, unseen full-text details, novel research gaps or experimental proposals. New prompt behavior has deterministic boundary tests but has not been benchmarked on live provider responses in this change. Abstract-only coverage remains incomplete coverage of the full papers. Additional selected papers do not guarantee complete scientific information.
