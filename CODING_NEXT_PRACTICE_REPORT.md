# Coding Agent: Personalized Next Practice

Implemented in PHSS_Web_App only. The original PHSS_Git Streamlit project was not changed.

## Student experience

After Submit & evaluate completes, a Practise this next card appears below submission feedback. It shows the recommended task, topic, difficulty, the existing policy's explanation, supplied-test results and any evaluation-reported misconceptions. Start recommended practice opens the actual exercise in the existing editor. A Practice focus card carries the reason into the next activity.

Successful submissions can open a different verified exercise at the policy-selected difficulty. Failed submissions offer a focused retry or an available easier exercise; unresolved issues cannot cause an increase in difficulty. An active cognitive conflict requires the existing diagnostic first. At the end of the curated progression or for custom topics, a different AI-generated variant is requested only after an explicit click and validated by the existing bounded generator.

The feature observes the original evaluated submission and updated shared CACM, uses CodingAgent.choose_action, acts through the existing coding workflow, and leaves the next student submission to provide fresh assessment evidence. Merely viewing or starting a recommendation creates no evidence or mastery. It does not replace the orchestrator.

## Safeguards and recovery

- Recommendations require a completed original practice assessment, not a standalone AI review or pending assessment.
- A recommendation token is recomputed from the current submission, exercise and cognitive state. Stale, repeated and other-profile starts are rejected.
- Topic-switch and next-practice operations preserve edited drafts through existing persistence.
- Starting next practice retains the plan and resets only its current step's assessment baseline.
- Focus and active exercise recover after refresh/restart; recommendations are derived again from saved evidence.
- Retry retains submission deduplication, so resubmitting identical code does not add mastery twice.
- Generation has at most two candidate attempts. Matching previous behavioral contracts or matching titles are rejected. Failure retains the original exercise, code and assessment.
- Generated reference solutions are removed from the public exercise API response.

## Exact files

Created:
- backend/coding_recommendations.py
- backend/tests/test_coding_recommendations.py
- frontend/e2e/coding-recommendations.spec.ts
- CODING_NEXT_PRACTICE_REPORT.md

Modified:
- app/coding_agent/open_topic.py
- app/persistence/session_recovery.py
- backend/main.py
- backend/service.py
- frontend/src/App.tsx
- WEB_FILES_CHANGED.json

Generated build, screenshots, test databases and source backups remain ignored under their existing directories.

## Executed verification

All executed with deterministic offline provider fixtures; no paid live AI calls were used.

- `.venv/Scripts/python.exe -B -m pytest backend/tests -q`: 77 passed, including 11 new recommendation tests. One existing Starlette/httpx deprecation warning.
- `.venv/Scripts/python.exe -B tools/evaluate_offline.py --only test_open_topic_coding`: 16 unittest executions passed; zero skipped.
- `.venv/Scripts/python.exe -B tools/evaluate_offline.py --only test_verified_coding_catalog`: 10 unittest executions passed; zero skipped.
- `.venv/Scripts/python.exe -B tools/evaluate_offline.py --only test_persistence_streamlit`: 8 unittest executions passed; zero skipped.
- `npm.cmd --prefix frontend run build`: passed TypeScript checking and production build; existing large Monaco chunk warning.
- From frontend: `npx.cmd playwright test coding-recommendations.spec.ts coding-workflow.spec.ts learning-quiz.spec.ts loading.spec.ts agent-buttons.spec.ts topic-options.spec.ts`: 7 passed.
- After improving screenshot synchronization: `npx.cmd playwright test coding-recommendations.spec.ts`: 1 passed again.

Browser tests exercised actual editor submission, supplied-test evaluation, next-exercise navigation, unchanged cognitive state on navigation, draft preservation and refresh recovery. They also checked existing coding review, learning quiz labels, topic controls, direct buttons and lazy research loading. The entire browser suite was not run.

Screenshots: data/web-e2e/screenshots/coding-recommendation-card.png and coding-next-practice.png. These use synthetic offline student profiles.

## Manual verification

1. Open http://127.0.0.1:8000 and press Ctrl+F5.
2. Choose Coding Agent or enter Give me a coding problem on Arrays.
3. Submit a solution using Submit & evaluate.
4. Below feedback, inspect Practise this next and its actual difficulty and evidence.
5. Click Start recommended practice. Check the new exercise or targeted retry and Practice focus.
6. Refresh, return to Study workspace and verify the exercise/focus remain saved.
7. Submit an incorrect solution to check revision guidance. Resolve any diagnosed cognitive conflict before progressing.

## Limits

Recommendations currently remain within the evaluated topic. Difficulty selection uses the existing rule-based Coding Agent policy, whose mastery estimates have not been calibrated by a real-student study. Generated variants require a configured available provider; limited supplied tests cannot prove universal correctness or independently validate an AI-authored specification. Cosmetic/contract duplicate detection is conservative and does not establish semantic novelty. A targeted retry intentionally reuses the exercise rather than fabricating a different task. Standalone code review remains separate from assessed practice.
