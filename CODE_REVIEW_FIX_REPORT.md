# Standalone code-review fix - 21 October 2026

Pasted-code correctness/debugging requests now enter a standalone review workflow in PHSS_Web_App rather than generating a replacement exercise. PHSS_Git remains unchanged.

## Behavior

- Existing semantic QueryRouter returns coding_mode=review or practice. The existing conservative local fallback recognizes an explicit review request outside the source code when semantic routing is unavailable; it does not replace the semantic router.
- Source is extracted from a single Python fence or an unfenced snippet with surrounding review instructions separated. It is not rewritten by a model during extraction. Ambiguous multiple snippets ask the student to choose one in the review editor.
- The review workflow uses existing CodeReviewEngine, AICodeReviewer, GuidedCodeReviewCoordinator and CorrectionVerifier. No behavioral tests are invented. Original code is not executed, and proposed corrections remain unverified by execution.
- The student sees their source in Monaco, an expected-behavior/context field, deterministic syntax inspection, explained issues, hints and suggested corrected code when supplied by the reviewer. Unclear intent may need student context; syntax validity is not a logical correctness verdict.
- A completed identical review is reused. Explicit edits invalidate the old response; failures retain the draft and allow explicit retry. Drafts/results persist by profile and recover after refresh/restart. Existing coding exercises and student submissions are preserved separately.
- No standalone review, suggested correction or navigation creates mastery evidence. Existing exercise assessment is unchanged.
- Older saved QueryRoute snapshots decode with practice as the default. Existing activities can use Review my own code instead to open the new workflow without resubmitting the query.

## Modified files

- `backend/service.py`
- `backend/main.py`
- `app/orchestrator/query_router.py`
- `app/persistence/session_recovery.py`
- `app/persistence/state_codec.py`
- `frontend/src/App.tsx`
- `frontend/src/style.css`
- `tools/web_fixture_server.py`
- `frontend/e2e/workspace.spec.ts`

## Created files

- `app/coding_agent/review_request.py`
- `backend/tests/test_code_review_flow.py`
- `CODE_REVIEW_FIX_REPORT.md`

Generated frontend/dist was rebuilt. Source backups are under data/source_backups/standalone_code_review_20261021; no original student database or secrets were copied. No environment changes or dependency installations were required. No commits/pushes/resets/clean operations were performed.

## Actual verification

- Full web API suite: 28 passed, one existing Starlette/httpx deprecation warning. Command: `.venv/Scripts/python.exe -B -m pytest backend/tests -q --tb=short --junitxml=data/code-review-api-results.xml`.
- Focused standalone review module: 10 passed. Tests include real reviewer response parsing, no exercise generation or execution, unchanged evidence, syntax errors, corrected-code labels, context edits, failed-provider retries, duplicate reuse, profile isolation, process restart, old snapshot compatibility and source-text boundaries.
- Chrome end-to-end suite: 8 passed, including the new actual React review workflow and refresh recovery. Existing Learning/Coding/Research scenarios also passed. Command: `npx.cmd playwright test` from frontend.
- Existing unified-query refinement: 11 unittest executions passed, data/evaluation/20261020T195014654164Z.
- Existing student persistence: 7 unittest executions passed, data/evaluation/20261020T195113814391Z.
- Existing code review engine script passed, data/evaluation/20261020T195125831157Z.
- Existing guided review coordinator script passed on isolated retry, data/evaluation/20261021T023409287815Z. Its earlier run timed out at the harness limit; that result remains at data/evaluation/20261020T195131630818Z and is not claimed as a pass.
- `npm.cmd --prefix frontend run build`: TypeScript and production build passed. The inherited large lazy-loaded editor bundle warning remains.
- All 318 PHSS_Git source hashes matched the original copy manifest. This fix changes the new project's router/codec/adapter files; the original project's copies were untouched.
- Real server at http://127.0.0.1:8000 returned healthy and exposes the new code-review API. Provider configuration is present. No paid live review was run during verification; provider calls in tests use explicitly offline fixtures.

The full 67-case inherited suite was not rerun for this focused change. Only the existing regression cases listed above are claimed for this fix.

## Manual check

1. Hard-refresh http://127.0.0.1:8000 with Ctrl+Shift+R.
2. Paste a Python program followed by `Is this code correct? Please explain errors and suggest a correction.` into the common query input and click Start. A single python fenced block also works.
3. Confirm Check my code is displayed with your original source, not a generated exercise.
4. Supply intended behavior/input/output when needed, then click Check my code. Review the explanations and suggested code. Corrections are labelled as unverified without behavioral tests.
5. Save edits with Save code draft and refresh; continue the study workspace to recover them.
6. For an already-open generated exercise from before this fix, use Review my own code instead, or resubmit your original request.

The server on port 8000 started by Codex was restarted. A separate user-started port-8001 server was left untouched; restart it manually before using the new backend there. No API key or .env content is included in this report.

Screenshot using offline synthetic provider responses: data/web-e2e/screenshots/standalone-code-review.png.
