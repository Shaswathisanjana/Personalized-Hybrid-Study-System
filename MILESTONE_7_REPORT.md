# Milestone 7: Unified three-agent student journey

Implemented on 20 October 2026 within the existing PHSS application. Milestone 8 has not begun.

## Student-facing behavior

Student View now uses a shared application service for natural-language requests. Learning requests retain the existing lesson/resource execution. Coding and Research intents provide links into verified coding practice and recoverable research analysis. Combined requests retain each selected activity. Unsupported coding topics are identified explicitly; they are not relabelled as supported exercises.

The **Continue studying** panel appears below the content on Student View, Advanced Coding Agent and Advanced Research Agent. It carries one selected topic across activities, shows the current evidence sources and actual agent recommendations, and offers consistent Continue learning / Continue coding practice / Continue research controls. A new study request updates the shared topic. Unassessed topics are labelled unassessed rather than displaying the neutral prior as demonstrated understanding.

Handoffs are saved with a student owner and applied before widgets are created. They prepare the next workflow without generating content, submitting answers, loading a replacement exercise or creating mastery evidence. Existing learning quizzes, coding drafts and research jobs remain saved. Returning to a workflow restores its active work. Learning handoffs prepare the goal and request; coding handoffs select the exact supported concept; research handoffs prefill the topic and personalization concept.

The Coding and Research pages obtain their workflows through the shared service, bound to the selected student and the same cognitive engine. Recommendations are recomputed from current shared state. A genuine conflict exposes a Resolve conflicting evidence handoff to the existing diagnostic workflow, including aliases such as Python Recursion / Recursion. Completed resolution removes the conflict recommendation; no conflict is manufactured for navigation or demonstration.

The older orchestrator API and saved output types remain compatible. The main UI deliberately uses richer workflow handoffs for new coding/research requests. Provider work still requires the destination page's explicit Generate/Load/Submit action. The original Start action begins a new request and retains its existing practice-reset behavior; switching through the new Continue controls preserves an unfinished practice session.

## Verified shared-state scenario

`test_student_journey.py` contains a controlled, simulated end-to-end scenario. It uses actual learning/practice services, the real original-code subprocess evaluator with a controlled semantic response, source-grounded research context, assessment transactions, the real cognitive engine and diagnostic resolver.

| Step | Recorded attempts | Verified behavior |
| --- | ---: | --- |
| Unassessed Recursion | 0 | Easy coding and introductory research; preview creates no evidence |
| Five correct learning answers | 5 | Coding difficulty and Research personalization change from the initial recommendations |
| Unfinished code submitted to actual behavioral tests | 6 | Objective failures yield a zero-performance coding evaluation; genuine cross-agent conflict appears |
| Incorrect research comprehension answer | 7 | Research assessment contributes its own evidence; all three agent sources are present and policies request diagnostics |
| Correct diagnostic answer | 8 | Existing resolver resolves the disagreement and all three policies leave diagnostic mode |
| Snapshot restored | 8 | Attempts, mastery, source counts and resolved conflict state remain; aliases still refer to one concept |

The answers, paper and evaluator responses are clearly labelled offline fixtures. This verifies integration and state propagation, not measured educational improvement or real-student learning outcomes. Research quotes are checked against the fixture abstract; no production links or findings were invented.

## Exact files

| Status | File | Purpose |
| --- | --- | --- |
| Created | `app/orchestrator/student_journey.py` | Pure shared-state observation, request handling, owner-scoped handoffs and workflow binding |
| Created | `app/orchestrator/streamlit_journey.py` | Common navigation/recommendation panel and natural-request handoff cards |
| Created | `test_student_journey.py` | Seven service, scope, persistence and real CACM propagation tests |
| Created | `test_student_journey_streamlit.py` | Five actual main-app workflow-switch and diagnostic tests |
| Modified | `review_ui.py` | Use the journey service, consume saved navigation, update topic context and display shared controls |
| Modified | `app/coding_agent/streamlit_page.py` | Obtain the coding workflow from the shared application service |
| Modified | `app/coding_agent/streamlit_review.py` | Correct the outdated introductory-only exercise-bank description |
| Modified | `app/research_agent/streamlit_page.py` | Persistent research input keys and shared coordinator binding |
| Modified | `app/persistence/session_recovery.py` | Persist navigation, topic, page and research input context |
| Modified | `app/persistence/streamlit_state.py` | Clear journey drafts on profile switch and preserve the current view for a fresh profile |

This report is also new. Original affected files, protected-test copies and the local regression harness are in `.milestone_backups/milestone7_20261020/` (ignored by Git). No new snapshot data classes or SQLite schema changes were required. Existing snapshots remain readable; new UI metadata should be used with the current code when restoring saved state.

## Verification

**120 distinct unittest tests passed across the verification runs**: 108 previous tests and 12 new journey tests. The initial 120-test run passed 119 and exposed one Research profile-switch error. The navigation change had returned a fresh profile to Student View; the existing Research test correctly found that its page state was absent. The fix preserves the current page for profiles without a saved page, while clearing the previous student's activity data. A saved page still takes precedence.

After that fix, the final applicable batch passed **110/110 tests**. The ten unchanged catalog/evaluator tests had already passed in the broader run. No existing assertion was weakened. The new isolation test additionally checks that a fresh profile's research topic and journey draft are empty. The final topic-context update was followed by another successful **5/5 journey UI** run.

Final applicable batch executed:

```powershell
python -B -c "import sys; sys.path.insert(0,'.venv/Lib/site-packages'); import unittest; unittest.main(module=None, argv=['unittest','test_student_journey','test_student_journey_streamlit','test_research_analysis_recovery','test_research_analysis_streamlit','test_coding_practice_streamlit','test_learning_study_planner','test_learning_study_plan_streamlit','test_assessment_transactions','test_assessment_transactions_streamlit','test_concept_identity','test_concept_migration','test_student_persistence','test_assessment_recovery','test_persistence_streamlit'], verbosity=1)"
```

Final focused UI check executed:

```powershell
python -B -c "import sys; sys.path.insert(0,'.venv/Lib/site-packages'); import unittest; unittest.main(module=None, argv=['unittest','test_student_journey_streamlit'], verbosity=1)"
```

All **41 standalone regression scripts passed** through the existing local audit harness, with external socket connections blocked and Windows loopback connections allowed for Streamlit:

```powershell
python -B .milestone_backups/milestone7_20261020/run_offline_checks.py
```

All **297 Python files** discovered by `rg --files -g '*.py'` passed syntax parsing. Scoped `git diff --check` passed. SHA-256 comparisons confirmed both protected uncommitted files (`test_evidence_store.py`, `test_misconception_analyzer.py`) are unchanged. Existing uncommitted work was preserved; no files were deleted, dependencies installed, environment files changed, commits made or pushes performed.

## Manual acceptance and remaining limits

1. In Student View, request coding and research on Recursion. Open coding practice, load the recommended exercise and write a draft.
2. Expand Continue studying and choose Continue research. The Research topic/concept should be prefilled. Refresh, then return to coding practice and confirm the draft remains.
3. Start a learning quiz, switch to Research and return through Continue learning. The same unanswered question and session should remain.
4. Choose a custom topic without verified exercises. Coding should be unavailable for that exact topic while Learning and Research remain accessible.
5. With genuine contradictory assessments, use Resolve conflicting evidence. Complete a diagnostic and inspect the refreshed recommendations and recorded evidence sources.
6. Switch profiles and confirm topic, inputs, drafts, analysis and assessment records remain isolated.

Live semantic routing, provider-generated content and manual browser interactions were not exercised. Automated UI tests used temporary SQLite stores, controlled providers and blocked external connections. Existing limitations still apply: calibrated cognitive thresholds are not established, verified coding covers six concepts, local code execution is not a hostile-code sandbox, and research uses available abstracts with bounded retrieval.

Stop here for approval before Milestone 8: reproducible evaluation and final-year deliverables.
