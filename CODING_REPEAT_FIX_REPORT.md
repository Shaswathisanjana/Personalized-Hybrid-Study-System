# Coding next-exercise repeat fix

## Reproduced issue

The previous implementation checked the proposed next task against only the active exercise. Reopening a topic always loaded its fixed catalogue task, and the next-practice policy could return to an earlier completed catalogue task after a generated variant. The common query path also started a new workspace rather than resuming assessed coding recommendations. A deliberate failed-task retry used the same new-practice wording.

An offline regression reproduced the reset: after completing the first and subsequent Arrays exercises, requesting Arrays again returned HTTP 200 and reinstalled the completed catalogue exercise as new. That assertion failed before the fix.

## Changes

- Profile-owned completed-task receipts retain topic, title, difficulty, behavioral-contract signature and source assessment identity.
- Existing committed coding-assessment receipts are read to recover earlier completions; no reassessment or mastery update is needed.
- After a successful assessment, recommendations and topic reopening exclude known completed tasks. New generated variants are checked against all known completed contracts/titles and the current task.
- Contract signatures ignore function renaming, test order, duplicate test rows and cosmetic test names. This detects those disguises but does not prove semantic novelty for every possible generated task.
- Semantic routing receives quoted saved coding context and supports an explicit next_practice workflow mode. A typed follow-up uses the same recommendation as the button rather than resetting the plan. Explicit topic changes take precedence. The existing provider-outage fallback handles only recognised explicit follow-ups.
- Typed follow-ups preserve an edited coding draft, the plan identity/remaining steps and shared cognitive state.
- Failed submissions are visibly labelled Revise this exercise or Revision practice. Reusing a task for remediation is intentional and is not presented as a fresh successfully completed problem.
- Pending assessment, conflict diagnostics, submission deduplication, student isolation, the navy/teal palette and research/learning workflows remain in place.
- Generation is still bounded to two attempts. Invalid or repeated provider candidates cause a recoverable failure while retaining the previous exercise, code and assessment.

## Exact files

Created:
- backend/coding_history.py
- CODING_REPEAT_FIX_REPORT.md

Modified:
- app/coding_agent/open_topic.py
- app/orchestrator/query_router.py
- app/persistence/session_recovery.py
- backend/coding_recommendations.py
- backend/main.py
- backend/service.py
- backend/tests/test_coding_recommendations.py
- frontend/src/App.tsx
- frontend/e2e/coding-recommendations.spec.ts
- test_unified_query_refinement.py (controlled semantic-provider fixture)
- tools/web_fixture_server.py (offline browser-provider fixture)
- WEB_FILES_CHANGED.json

The original PHSS_Git application, thesis deliverables and stylesheet were not modified by this fix.

## Executed tests

All verification used deterministic offline providers, not paid live AI calls.

- Before fix: the new topic-reopening regression failed, confirming the repeated-task reset.
- Final `.venv/Scripts/python.exe -B -m pytest backend/tests -q`: 87 passed in 92.52 seconds; one existing Starlette/httpx deprecation warning. The recommendation module now contains 21 tests.
- `.venv/Scripts/python.exe -B tools/evaluate_offline.py --only test_open_topic_coding`: 16 unittest executions passed, zero skipped.
- `.venv/Scripts/python.exe -B tools/evaluate_offline.py --only test_unified_query_refinement`: 11 unittest executions passed, zero skipped.
- `npm.cmd --prefix frontend run build`: TypeScript and production build passed; existing large Monaco chunk warning.
- From frontend: `npx.cmd playwright test coding-recommendations.spec.ts coding-workflow.spec.ts learning-quiz.spec.ts agent-buttons.spec.ts topic-options.spec.ts loading.spec.ts progress.spec.ts`: final run 11 passed in 41.8 seconds.
- The first selected browser run had 10 passes and one test-only locator failure because Monaco adds hidden role=alert nodes. The assertion was scoped to the application error banner, then all 11 were rerun successfully.

The tests cover successful practice advancement, typed next requests, current-plan/draft preservation, intentional failed-task revision, multiple-task cycle avoidance, refresh/restart, old receipt recovery, foreign-profile rejection, provider failure and disguised duplicate contracts. The entire historical browser suite was not run.

## Manual check

1. Hard-refresh the web app with Ctrl+F5.
2. Start an Arrays exercise, write a solution and Submit & evaluate.
3. After a successful evaluation, use Start recommended practice or type Give me the next problem in the common input.
4. Confirm the new task differs from the completed task and that navigation did not add assessment evidence.
5. Refresh to check recovery. Existing completed tasks with committed receipts should remain excluded from new practice.
6. Submit incorrect code to confirm that the UI explicitly offers revision, which may intentionally reuse a task.

## Limits

A provider must supply a different valid package when the finite catalogue has no suitable unseen task. If it cannot, the application preserves work and reports failure rather than claiming that the old task is new. Supplied contract comparisons do not establish full program equivalence or guarantee the educational novelty of every generated problem. Legacy assessments without retained task/test receipts cannot be reconstructed. Existing same-topic recommendation and rule-based difficulty policies are retained.
