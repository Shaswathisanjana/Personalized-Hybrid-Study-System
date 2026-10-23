# Milestone 4: Learning Agent experience

Implemented on 20 October 2026 within the existing PHSS application. Milestone 5 has not begun.

## Behavior delivered

- **My Study Plan** saves a goal per student, supports all 50 bank topics and custom topics, and recomputes recommendations from shared CACM state on each render.
- Known prerequisites appear in dependency order. An unassessed neutral prior never satisfies a prerequisite. Planned progression checks current prerequisites again before generating content. Reassessment of an already studied weak topic remains available even when its prerequisites need work.
- Revision suggestions use the latest actual assessment evidence from any agent. Opening lessons, resources or plans does not postpone revision or increase mastery. Readiness uses the existing .70 mastery/.50 confidence thresholds; seven-day revision is a scheduling heuristic, not a measured forgetting model.
- Existing active/uncertain misconception hypotheses carry into subsequent practice sessions. Remediation begins easy; uncertain hypotheses receive medium verification. Generated question target labels must match the requested hypotheses exactly.
- A fully correct answer to a targeted question can contradict its existing hypothesis using the existing misconception tracker. This update shares the cognitive evidence transaction, rollback and deduplication receipt. A generic correct answer cannot contradict an unrelated hypothesis. The existing tracker thresholds and increments remain unchanged.
- Genuine cross-agent conflicts can launch the existing CACM diagnostic workflow from the Learning page. Questions, answers and results survive refresh. Interrupted submissions require explicit Resume and reuse saved stages.
- Detailed completed learning history comes from saved completed assessment outcomes, with session deduplication and student isolation. Earlier aggregate progress remains intact; missing historical detail is not invented.
- Planned lessons use the existing content provider and real resource recommender. The existing topic browser, resource ranking, format filters, three initial resources plus View More, and 5/10/15/20-question assessments remain available.
- Opening a planned lesson is disabled during an unfinished practice or diagnostic assessment. Generation failure preserves the current displayed activity. Restart Current Activity retains the study goal; explicitly clearing the student's progress removes it.

## Exact application and test files

| Status | File | Purpose |
| --- | --- | --- |
| Created | `app/learning_agent/study_planner.py` | Pure planning, prerequisites, revision and completed-session history |
| Created | `app/learning_agent/diagnostic_bridge.py` | Access to genuine CACM diagnostics using the learning providers |
| Created | `app/learning_agent/streamlit_study_plan.py` | Goal, plan, history and diagnostic controls |
| Created | `test_learning_study_planner.py` | 19 deterministic planning/remediation tests |
| Created | `test_learning_study_plan_streamlit.py` | 6 offline tests of the actual Streamlit page |
| Modified | `app/learning_agent/agent.py` | Prioritize active and uncertain misconception reassessment |
| Modified | `app/learning_agent/practice_policy.py` | Persistent misconception targets and initial remediation difficulty |
| Modified | `app/learning_agent/gemini_quiz_generator.py` | Request exact target descriptions for traceable reassessment |
| Modified | `app/learning_agent/runtime.py` | Execute planned activities and stage targeted contradiction evidence |
| Modified | `app/cognitive/cognitive_engine.py` | Atomic, deduplicated contradiction updates within evidence processing |
| Modified | `app/persistence/session_recovery.py` | Save goals and learning diagnostic state; reconnect the shared engine |
| Modified | `app/persistence/assessment_recovery.py` | Resume interrupted learning diagnostic submissions |
| Modified | `app/persistence/streamlit_state.py` | Retain goals when discarding interrupted activity |
| Modified | `review_ui.py` | Mount the planning panel and preserve goals on activity restart |

This report is also new. Existing-file backups and the local regression harness are in `.milestone_backups/milestone4_20261020_114740/` (ignored by Git). Earlier changes in the working tree are not attributed to this milestone. In particular, existing changes to resource retrieval, progress tracking and other agents were preserved.

## Commands and results

The existing dependency directory was used through a process-local import path. No dependency installation or environment-file change was required.

Final combined suite, **72 tests passed** (25 new, 47 previous):

```powershell
python -B -c "import sys; sys.path.insert(0, '.venv/Lib/site-packages'); import unittest; unittest.main(module=None, argv=['unittest', 'test_learning_study_planner', 'test_learning_study_plan_streamlit', 'test_assessment_transactions', 'test_assessment_transactions_streamlit', 'test_concept_identity', 'test_concept_migration', 'test_student_persistence', 'test_assessment_recovery', 'test_persistence_streamlit'], verbosity=1)"
```

Selected standalone regression scripts, **23 passed**, each run separately with external socket connections blocked (Streamlit's Windows loopback sockets allowed):

```powershell
python -B .milestone_backups/milestone4_20261020_114740/run_offline_checks.py
```

The scripts cover adaptive quizzes, automatic diagnostics, learning progress, the topic bank, assessment length, coding submission/review/diagnostics, research assessment/diagnostics/offline workflow, the three-agent CACM loop, conflict resolution, resource format filtering, resource relevance and ranking independence from topic tags. The exact script list and invocation are in the harness.

All four assessment lengths (5/10/15/20) additionally completed in the new deterministic tests, with one evidence entry and one cognitive attempt per answer. The Streamlit tests cover goal refresh/profile isolation/restart, custom goals, prerequisite activity opening without evidence, preservation of active practice, genuine-conflict diagnostics, interrupted diagnostic recovery, and format filtering with three resources plus View More.

Syntax check, **285 Python files passed**:

```powershell
python -B -c "import ast, pathlib, subprocess; paths=[pathlib.Path(p) for p in subprocess.check_output(['rg','--files','-g','*.py'], text=True).splitlines()]; [ast.parse(p.read_text(encoding='utf-8-sig'), filename=str(p)) for p in paths]; print('Syntax OK:',len(paths),'Python files')"
```

Scoped `git diff --check` passed. A broader whitespace scan found three pre-existing trailing-whitespace lines in `review_ui.py`; comparison with the milestone backup confirmed they predate this work, and they were left untouched. SHA-256 comparisons confirmed both protected tests (`test_evidence_store.py`, `test_misconception_analyzer.py`) are unchanged from the milestone backup.

During verification, one initial Streamlit run timed out; its isolated retry, the complete new suite, and the final combined suite passed. One new test initially assumed confidence .40 was uncertain. Inspection confirmed the existing tracker treats .40 as active; the tests now explicitly verify that boundary and separately exercise the uncertain band. Tracker thresholds were not changed.

## Limits and manual acceptance

No paid/live Gemini or resource API calls were made. Actual provider quality, current source availability and a manual browser session remain unverified. Automated UI tests used clearly identified fixtures and temporary SQLite databases, without using the application's real student database. Resource fixture URLs use reserved `example.org` addresses only in tests.

These readiness and remediation rules are prototype engineering heuristics. Correct-target attribution relies on generated question labels and answer evaluation; it is not independent evidence of educational effectiveness. Custom topics have no invented prerequisite graph. Historical detailed sessions are shown only where actual saved outcomes exist.

In Streamlit, verify:

1. Select a student and save **Python Recursion** in **My Study Plan**. For an unassessed profile, **Python Basics** should be first, followed by **Python Functions**.
2. Open the recommended activity. Resource filters and View More should work; merely viewing content should leave cognitive attempts unchanged.
3. Begin a 5-question practice session. Opening another planned activity should be disabled until completion or an explicit activity restart.
4. Complete the quiz, refresh, and confirm the goal, progress and detailed completed session remain for that student. Switch profiles and confirm isolation.
5. When genuine assessed evidence produces a conflict, generate and answer the learning diagnostic. Refresh before submission to check question recovery. A provider failure during submission should offer explicit Resume after refresh.

No files were deleted, no commits or pushes were made, and the protected uncommitted tests were preserved. Stop here for approval before Milestone 5 (Coding Agent).
