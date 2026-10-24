# Coding topic chooser and submission/review resilience

## Student-facing changes

A collapsed Choose a coding topic section appears above Coding Agent practice. It lists the six topics supported by actual verified Python exercises: Recursion, Prime Numbers, Arrays, Strings, Python Functions and Searching Algorithms. Selecting a topic uses the existing autonomous query/orchestration workflow. Arbitrary topics remain available through the common query box.

Starting another topic preserves the latest edited draft per previous topic for reference in collapsed Saved draft entries. Drafts are profile scoped, recover after refresh, and are not automatically applied to a different exercise. Previously evaluated evidence remains intact. Saving a draft and starting the selected topic uses the new saved revision to avoid false stale-page errors.

Submit & evaluate continues to assess the student's original submitted source. It now persists that source before evaluation starts. If local tests completed but the full conceptual assessment fails, their actual results are retained and displayed as local-test evidence while the assessment remains pending. Use Resume interrupted assessment to retry. A local execution preview is not a new cognitive score and never supplies fabricated AI feedback. If evaluation fails before local execution (for example, missing provider configuration), no execution results are invented.

Review & verify correction still uses the last evaluated submission and checks suggested corrections against supplied tests. Review failures display an explicit retry message while retaining the assessed submission and its evidence. AI corrections do not become mastery evidence. Feedback identifies that it refers to the last submitted code, so subsequent editor changes must be submitted again.

## Exact files

Modified: backend/main.py; backend/service.py; app/coding_agent/evaluator.py; app/persistence/session_recovery.py; frontend/src/App.tsx; test_unified_query_refinement.py; WEB_FILES_CHANGED.json.
Created: backend/tests/test_coding_topics_submission.py; frontend/e2e/coding-workflow.spec.ts; CODING_TOPICS_SUBMISSION_REPORT.md.
Generated frontend/dist was rebuilt and remains ignored. Local backups: data/source_backups/coding_topics_submission_20261024. No original PHSS_Git/Streamlit source changes or environment/package changes.

## Executed verification

- Final TypeScript/Vite build passed (existing large-bundle warning remains).
- Full offline backend suite: 62 passed, one existing Starlette deprecation warning, 42.42 seconds.
- Four new API scenarios cover the real topic catalog and saved drafts/student isolation, actual original-code execution and deduplication, provider failure with retained local results and resume, and review failure without extra evidence.
- Existing offline verified coding catalog: 10 passed; existing persistence/assessment recovery: 8 passed. No skipped tests.
- Final Chrome run: 4 passed, 22.5 seconds. Covers exact original source entered through the real editor and submitted via the real button, actual behavioral results, correction review, choosing Strings after editing an Arrays draft, preserved drafts and refresh, standalone code review, hints/draft recovery and the previous learning-topic quiz fix.
- Intermediate browser attempts failed because the automation focused Monaco's hidden compatibility textarea, then simulated multiline typing that triggered automatic indentation. The final regression uses the visible accessible editor and native clipboard paste, asserts the exact submitted source and then asserts actual test results. These failed attempts were not claimed as successful checks.
- Restarted only the verified separate web-app servers on ports 8000 and 8001.

## Manual verification

Refresh with Ctrl+F5 and open a coding practice activity. Click Choose a coding topic, select a topic and click Start selected topic. The list stays collapsed until clicked. Enter a solution matching the displayed function contract; click Submit & evaluate. Review the real test outputs and educational feedback. Click Review & verify correction for the last submitted code. Modify your draft, select another topic and check the saved draft entry. Refresh and confirm the current exercise and saved draft survive.

If full assessment is interrupted, inspect any local-test evidence and click Resume interrupted assessment after the provider is available. Do not interpret passing a bounded supplied test suite as proof of universal correctness. Syntax failures and failing behavioral cases are legitimate evaluation results, not broken buttons.

## Limits

The reported live failure was not independently reproduced against the paid provider. Verification uses deterministic offline provider responses at the provider boundary, while static analysis, Python execution, persistence, CACM transactions and browser controls are real. Live AI evaluation/review still depends on valid configuration and provider availability. This change repairs concrete failure-recovery/data-loss paths and confirms the controls operate end to end; it does not guarantee provider uptime. The topic dropdown currently lists the six verified topics, not every possible programming subject. Other topics use existing generated-exercise workflows through the common query input. Local code execution retains the project's existing trusted-local-code limitations.
