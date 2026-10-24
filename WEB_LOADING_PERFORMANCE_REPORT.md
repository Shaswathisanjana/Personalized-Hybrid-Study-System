# Web loading investigation and targeted improvements

## What was measured

Read-only requests against the real local app before the change: health 178 ms, profile list 16 ms; two saved student snapshots 444 ms (cold) and 43 ms; their research views 71 ms/19,245 bytes and 69 ms/328,445 bytes. No student names, profile IDs, source text or secrets are recorded here. These observations do not measure paid AI generation latency.

The browser fetched the entire research collection on initial restoration and after starting any activity, even Learning/Coding. It also waited for research before displaying restored state. Independent educational resources were retrieved sequentially from YouTube, Wikipedia and official documentation. Those sources have existing individual network timeouts, so sequential waits can add together. Semantic routing, content generation, assessment and optional AI review still have real provider latency and existing retry bounds.

## Changes

- frontend/src/App.tsx loads research only when the active workflow requires it. Restored student state is set immediately, before research data if needed. Research still loads when explicitly entered, advanced to or retried, and saved report preferences still load for research. Learning and Coding avoid the irrelevant collection request.
- app/learning_agent/resources/multi_source_retriever.py runs independent read-only source requests in a bounded thread pool (maximum four workers). Results are collected in input order, so existing round-robin merging, deduplication, relevance filtering, partial-failure handling and all-source-failure behavior remain unchanged. Existing source timeouts are retained.
- frontend/src/components/LoadingStatus.tsx displays elapsed time after three seconds and a truthful keep-open message after eight seconds. Its timer is isolated in a small component rather than rerendering the entire editor every second. It does not display fabricated progress percentages or promise a completion time.
- backend/main.py adds Server-Timing duration headers to make future backend delays observable without recording prompts, answers or credentials.
- backend/tests/test_loading_performance.py tests real overlapping execution with a barrier (not fragile timing thresholds), deterministic result order, deduplication, partial/total failures and duration-header validity.
- frontend/e2e/loading.spec.ts verifies zero research downloads for initial non-research restoration, learning, learning refresh and coding, then verifies research loading and refresh recovery.
- WEB_FILES_CHANGED.json records the created files. This report is WEB_LOADING_PERFORMANCE_REPORT.md.

## Actual verification

- Final TypeScript/Vite production build: passed. Existing large editor-bundle warning remains; editor continues to load lazily.
- Complete offline backend suite: 66 passed, one existing Starlette deprecation warning, 41.18 seconds.
- Chrome browser suite: 5 passed, 23.4 seconds. Covers eliminated research requests, research restoration, actual coding submission/review and draft topic switching, adaptive learning quiz recovery, and both empty/populated responsive progress dashboards.
- Existing controlled test_multi_source_retriever.py and test_relevance_pipeline_integration.py: both scripts passed with outbound socket connections explicitly blocked. Round-robin merging/deduplication and CACM-aware relevance filtering remained intact.
- An initial attempt to select these scripts through evaluate_offline.py was rejected because they are not registered in its curated manifest; they were subsequently executed explicitly under the network guard. The live test_three_source_integration.py was not run.
- Synthetic three-source benchmark, each source fixed to 50 ms: 151.3 ms sequential versus 65.8 ms concurrent. This measures only synthetic source waits and is not a claimed production or end-to-end AI speedup.
- Initial backend collection failed because an existing UTF-8 BOM moved below a newly added import. The BOM was removed, then the complete suite was rerun successfully. No tests were skipped or timeout thresholds weakened.
- Restarted only verified PHSS_Web_App servers on ports 8000 and 8001. No paid provider generation, code submission or student-answer evaluation was run against real profiles during investigation.

## Use and remaining limits

Press Ctrl+F5. Learning/Coding should not wait for a research-library download. Real AI routing/generation and searches may still take seconds or longer during provider load. Resource lookups now overlap but still wait for their slowest configured source; concurrency cannot guarantee remote-service uptime. Server-Timing can be inspected in browser Network response headers to separate backend work from browser/transfer delays. The app still processes a workflow synchronously under its existing state lock; this change does not introduce background jobs, alter scoring, replace semantic routing or silently reuse stale cognitive recommendations. The investigation did not establish one exact cause for every slow operation because no live paid request was profiled. No Streamlit source, environment, student-record content or main-branch code was changed.
