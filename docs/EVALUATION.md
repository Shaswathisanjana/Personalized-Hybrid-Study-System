# Reproducible evaluation

## Commands and artifacts

```powershell
python -B tools/evaluate_offline.py --list
python -B tools/evaluate_offline.py
python -B tools/evaluate_offline.py --only test_student_journey
python -B -m unittest tools.test_evaluate_offline
```

The explicit `tools/offline_suite.json` now selects 26 unittest modules and 41 standalone scripts. Phases 2–4 added PDF, academic search/DOCX and open-topic coding checks. Phases 5–6 added `test_study_workspace` and `test_study_workspace_streamlit`. Each case runs in a separate process from the repository root with a default 300-second timeout. `--only` accepts an exact manifest entry; `--timeout` adjusts the per-case bound. Unknown selections fail before execution. Tests use temporary databases and fixtures, not the current student's app database.

The separate runner test command checks seven disposable subprocess scenarios: assertion success/failure, empty suite, nonzero script exit, missing file, timeout and blocked external TCP. These infrastructure tests are not included in the 26-module application count.

Each run produces ignored `data/evaluation/<UTC timestamp>/results.json`, `summary.md` and per-case logs/metrics. Results record the Python runtime, manifest hash, selected file hashes, exit statuses, durations and actual unittest counts. Standalone script success is a successful process exit, not a counted unit test or a claim that every printed demonstration has assertions. The inventory marks every other root `test_*.py` as **not_run**. A selected run is labelled selected, not a full evaluation.

The parent exits nonzero for missing selected files, nonzero child exits, missing unittest metrics, zero unittest count or timeout. Unittest skips remain explicitly recorded; they are not exercised assertions. Timeout logs do not retain partial child output. Review per-case logs for details.

The runner supplies dummy Gemini/YouTube keys to child processes and blocks non-loopback `socket.connect`/`connect_ex` calls there. Loopback is needed by Streamlit AppTest on Windows. This is a guard against accidental external TCP requests by trusted tests, not a firewall, credential vault or hostile-code sandbox. Child code execution is not comprehensively isolated; do not add unreviewed/live tests to the manifest. Existing `.env` is never edited. Logs should still be reviewed before sharing.

## Acceptance scenarios and evidence

| Requirement | Maintained check | Expected evidence |
| --- | --- | --- |
| Learning personalization | `test_learning_study_planner`, `test_learning_study_plan_streamlit` | Prerequisites, revision, remediation and saved history influence the plan; preview adds no mastery |
| Coding correctness | `test_verified_coding_catalog`, `test_coding_practice_streamlit` | 18 reference solutions execute against real subprocess tests; failed objective cases constrain evaluation; difficulty is applied |
| Open-topic coding | `test_open_topic_coding`, `test_open_topic_coding_streamlit` | Generated packages execute reference/starter/probe tests before publication; bounded failures, persisted original-code assessment, hints, correction review and student isolation |
| Unified student workspace | `test_study_workspace`, `test_study_workspace_streamlit` | Real inline activities, deferred preparation, ordered saved steps, original-code assessment, seven-paper selection, ownership validation, explicit retries and cross-agent difficulty propagation |
| Research grounding | `test_research_analysis_recovery`, `test_research_analysis_streamlit` | Rejected abstracts/duplicates do not satisfy targets; wrong-source summaries and invented quotes are rejected |
| Shared CACM and diagnostics | `test_student_journey` | Real assessed fixture sequence changes three policies, creates disagreement and resolves it through diagnostic evidence |
| Persistence | `test_student_persistence`, `test_persistence_streamlit` | Restore shared model, evidence and supported activity state; profiles remain separate; stale writes are rejected |
| Concept identity/migration | `test_concept_identity`, `test_concept_migration` | Exact aliases share a concept; distinct topics remain separate; old collisions are archived |
| Duplicate prevention | `test_assessment_transactions`, `test_assessment_recovery` | Retry reuses saved evaluations and receipts; changed submission is rejected; attempts are not recounted |
| Provider failures | `test_assessment_transactions`, `test_research_analysis_recovery` | Injected evaluation/follow-up/search/summary failures leave recoverable partial state |
| Streamlit recovery and navigation | `test_student_journey_streamlit`, `test_assessment_transactions_streamlit`, `test_persistence_streamlit` | Real AppTest runs preserve drafts/quizzes on workflow switches, restore profiles and require explicit resume |

The 41 scripts supplement these checks with existing learning, resource filtering, code review/hints, research export and diagnostic regressions. The manifest is the exact executable list. Other historical tests may require network access, credentials, manual interaction or review; their status is unknown in this evaluation. Do not replace the curated command with blanket discovery and call the results equivalent.

## Controlled integration scenario

`test_student_journey.test_actual_three_agent_evidence_conflict_diagnostic_and_replanning` uses actual services and cognitive updates with labelled synthetic answers, a paper fixture and controlled provider responses:

1. An unassessed Recursion topic has zero assessed attempts.
2. Five correct learning answers produce five attempts and change recommendations.
3. An unfinished original coding submission fails actual behavioral tests, producing attempt six and a genuine disagreement with learning evidence.
4. An incorrect research comprehension answer adds the third evidence source and attempt seven.
5. Correct diagnostic evidence resolves the existing conflict at attempt eight; policies leave diagnostic mode.
6. Persistence restores the same attempts, evidence and resolved state. Aliases refer to one concept and another student remains isolated.

This is deterministic software integration evidence. It is not eight real student observations or a measured learning gain. The research paper and responses are fixtures, not publishable findings or real citations.

## Separate validation still needed

The unified landing refinement adds `test_unified_query_refinement`: real router-response parsing, direct lesson/practice, custom linked-list exercises, academic search, uploaded-PDF comparison, contextual clarification and refresh recovery. See [the refinement report](../UNIFIED_QUERY_REFINEMENT_REPORT.md) for actual executed results and native-browser screenshots.

`python -B tools/browser_workspace_smoke.py` separately drives an existing headless Chrome/Edge browser against an isolated offline-backed Streamlit server. It checks actual DOM inputs, inline coding assessment, refresh/SQLite receipt preservation and research retrieval. Artifacts are saved in ignored `data/browser_smoke/`. It uses existing `websockets` and browser binaries, installs nothing and does not measure live-provider quality. Native Word rendering, file-picker/download behavior, accessibility and concurrent-load coverage remain separate checks. See [the unified workspace guide](UNIFIED_STUDY_WORKSPACE.md).

Live-provider smoke checks require explicit authorization, valid keys, a small budget and recorded dates/models. Measure retrieval shortfalls, quote support, answer quality, latency and costs without counting failed calls as successes. No live-provider check was performed for Milestone 8.

An educational study would require consent, a defined participant/sample protocol, a baseline or comparison condition, pre/post measures, a scoring rubric and appropriate analysis. No such results currently support claims of improved learning, calibrated mastery probabilities or reduced misconceptions in real students.
