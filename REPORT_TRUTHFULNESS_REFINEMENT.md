# Report evidence and interpretation refinement

The supplied research-report (2).docx now has 6/6 abstract-only chunks analyzed. Its remaining weaknesses are interpretation and report coverage: source-exact future-work quotations can be classified as implemented models, vague dataset mentions can look like dataset identities, and the saved six-section export omits evaluation, synthesis and other available sections. Verifying an exact quotation alone does not validate scientific correctness or field classification.

Modified: backend/research_reports.py.
Created: backend/tests/test_report_truthfulness.py and REPORT_TRUTHFULNESS_REFINEMENT.md.
Updated: WEB_FILES_CHANGED.json inventory. No changes to the original Streamlit project, environment, saved student analyses or supplied Word document.

Changes:
- Add an evidence summary with per-field counts and numbered references. Missing source evidence is not described as absence from the publication or proof of a research gap.
- Display sections not requested and instructions to select all sections. Existing user section selections remain respected.
- Label model excerpts as potentially implemented, reviewed or proposed, with role not independently verified. Label dataset descriptions whose dataset identity may be unspecified. Label findings as author-reported and unreproduced.
- Comparison includes available author-reported findings with exact page/chunk attribution, so a missing extracted metric field does not hide the reported result. It does not derive new metrics from percentages.
- Explicitly explain that different metrics, datasets, splits, thresholds and evaluation conditions prevent a valid cross-paper ranking without matching protocols.
- Replace generic gap/future-experiment generation in this web export with source-linked verification questions and literature-check steps. No new dataset, method, novelty claim or expected improvement is invented.
- Both Word and Markdown use the same updated evidence model; exports do not call providers or increase CACM mastery.
- Processing readiness now explicitly asks the student to review evidence coverage and source context. It does not claim scientific verification.

Verification:
- Five new report-truthfulness tests passed.
- Research report flow and reliability suite: 14 passed, one existing Starlette deprecation warning.
- Full backend suite: 46 passed, one intermittent coding-exercise validation test failed during the concurrent run. Isolated rerun of that test plus all 19 research-report tests: 20 passed, one existing warning (34.48 seconds). The initial full run is not represented as entirely passing.
- Existing offline Word export suite: 7 passed; existing full-text grounding suite: 4 passed.
- Chrome browser report preparation/PDF export checks: 2 passed (19.8 seconds), including refresh recovery. Both downloaded documents opened with python-docx, contain two tables, the evidence summary and comparison caveats. Both restarted local servers return HTTP 200 health.
- Original-source preservation: all 318 hashes match. No real student analysis, paid provider call or source reclassification was performed for testing.

Use: hard-refresh the app on port 8000 or 8001; open research; click Select all report sections; generate Word again. Already analyzed sources do not require another paid analysis merely to use the improved exporter. For more source detail, upload full PDFs and process those separately. Abstracts cannot guarantee datasets, reproducible procedures or full evaluation protocols. Exact-source checking cannot guarantee correct AI categorization; the report makes that boundary explicit. No absolute hallucination-free or fully scientifically validated claim is made. This remains an evidence-organizing research aid, not an independently verified systematic review.
