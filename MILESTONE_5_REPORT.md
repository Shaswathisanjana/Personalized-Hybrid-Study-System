# Milestone 5: Coding Agent

Implemented on 20 October 2026 within the existing PHSS project. Milestone 6 has not begun.

## Result

The Coding Agent's recommended difficulty now determines the loaded exercise. Easy, medium and hard select different tasks rather than relabelling the same question. Unassessed students begin with easy foundational practice; active misconception hypotheses request remediation, uncertain hypotheses request medium verification, and genuine cross-agent conflicts retain priority.

The bank now contains **18 exercises across six concepts**:

| Concept | Easy | Medium | Hard |
| --- | --- | --- | --- |
| Recursion | Factorial Using Recursion | Sum a Nested List Recursively | Recursive Binary Search |
| Prime Numbers | Check Prime Number | Prime Factorization | Primes in an Inclusive Range |
| Arrays | Find Maximum Element | Rotate a List to the Right | Maximum Contiguous Subarray Sum |
| Strings | Count Vowels | Compare Anagrams | Longest Substring Without Repeats |
| Python Functions | Clamp a Value | Operation Dispatcher | Composable Numeric Pipeline |
| Searching Algorithms | Find the First Matching Index | Iterative Binary Search | Lower Bound with Duplicate Values |

The original three easy tasks and their cases are retained. Each additional exercise has an explicit input/output contract, normal/boundary cases and three task-specific progressive hints. Reference implementations exist only in the offline tests. Difficulty levels are engineering judgments about task demands, not calibrated student-ability measurements.

The existing hybrid evaluator still combines static analysis, actual subprocess tests and semantic review. Semantic scoring can no longer override a failed predefined test: performance is capped by passed cases divided by all requested cases, and a correct classification requires all requested tests to pass. Cases skipped after a timeout remain in the denominator. This does not make passing tests proof of universal correctness, complexity or required programming techniques.

Review-to-practice mapping and the genuine-conflict diagnostic selector include the additional concepts through the same conservative concept identities. No unsupported topic aliases were added. The existing review, correction verification, submission deduplication, diagnostic intervention and shared CACM bridge remain in place.

Loaded exercises remain fixed while a student works, even if assessed evidence changes the recommendation. Older saved tasks are retained and identified as earlier specifications; loading a replacement requires the student's existing explicit Load Coding Exercise action. Refresh retains code, hints and assessment records without a schema change.

## Local execution limits

The UI now explains that submitted code runs locally in Python subprocesses with a **five-second wall-clock timeout per test**, including process startup. The default was increased from two seconds after correct reference solutions occasionally timed out during Windows subprocess startup. This matches the correction verifier's existing five-second setting. Infinite-loop tests explicitly use a shorter limit and verify early termination.

This remains a development runner, not a security sandbox. Submitted code has the user's file/network privileges. Memory, output size, CPU usage and descendant processes are not comprehensively isolated. A timeout can reflect a slow machine as well as non-terminating code. Use trusted submissions locally; a public multi-user grader would require separate isolation work.

## Exact files

| Status | File | Change |
| --- | --- | --- |
| Created | `app/coding_agent/exercise_catalog.py` | Fifteen additional specifications, cases and task-specific hint sets |
| Created | `test_verified_coding_catalog.py` | Ten offline catalog, policy, mapping and evaluation tests |
| Created | `test_coding_practice_streamlit.py` | Five tests of the actual main Streamlit application |
| Modified | `app/coding_agent/verified_exercises.py` | Six-concept catalog, real level selection, validation, independent returned data |
| Modified | `app/coding_agent/agent.py` | Evidence-aware foundational and misconception decisions |
| Modified | `app/coding_agent/streamlit_page.py` | Apply difficulty, expand choices, explain old tasks and execution limits |
| Modified | `app/coding_agent/agentic_review_coordinator.py` | Map exact supported identities to practice |
| Modified | `app/coding_agent/progressive_hint_engine.py` | Task-specific hints with existing progression and legacy compatibility |
| Modified | `app/coding_agent/streamlit_diagnostic.py` | Diagnostic selection for all supported coding concepts |
| Modified | `app/coding_agent/evaluator.py` | Behavioral results constrain semantic performance/correctness |
| Modified | `app/coding_agent/code_runner.py` | Five-second default wall-clock timeout |

This report is also new. Backups of all affected existing files, both protected tests and the local regression harness are in `.milestone_backups/milestone5_20261020/` (ignored by Git). Existing uncommitted changes outside these targeted edits were preserved.

## Verification and commands

**87 distinct unittest tests passed**, comprising 72 earlier tests and 15 new tests. They were executed in these successful batches (four UI tests overlap):

```powershell
python -B -c "import sys; sys.path.insert(0, '.venv/Lib/site-packages'); import unittest; unittest.main(module=None, argv=['unittest','test_verified_coding_catalog','test_coding_practice_streamlit'], verbosity=2)"
```

This batch passed 14 tests before the fifth UI test was added. It executes every reference implementation through the real subprocess runner, rejects unfinished starters, checks distinct levels and independent case data, exercises task-specific hints and conservative mappings, and verifies partial-failure/full-pass/timeout scoring against a controlled semantic response.

```powershell
python -B -c "import sys; sys.path.insert(0, '.venv/Lib/site-packages'); import unittest; unittest.main(module=None, argv=['unittest', 'test_coding_practice_streamlit', 'test_learning_study_planner', 'test_learning_study_plan_streamlit', 'test_assessment_transactions', 'test_assessment_transactions_streamlit', 'test_concept_identity', 'test_concept_migration', 'test_student_persistence', 'test_assessment_recovery', 'test_persistence_streamlit'], verbosity=1)"
```

The final batch passed 77 tests: all 72 earlier tests plus all five new coding UI tests. The UI tests cover recommended easy/medium/hard tasks, actual original-code assessment, refresh and duplicate prevention, hint persistence, profile isolation, preservation of legacy saved work, and genuine conflicts for an added concept.

Standalone regression scripts were run separately with external socket connections blocked and Windows loopback connections allowed:

```powershell
python -B .milestone_backups/milestone5_20261020/run_offline_checks.py
```

All **29 scripts passed**: the earlier 23 learning/coding/research/CACM/resource regressions plus progressive hints, adaptive hints, correction verification, guided review, static code review and misconception detection. The exact list is in the harness.

Initial verification exposed wall-clock timeouts for correct subprocess solutions, including an overly short .5-second limit in positive evaluator fixtures. Positive cases now use the application's five-second default. The infinite-loop fixture retains its .5-second limit. Assertions on reference outputs, case failures and scoring remain intact. A test-module import was also changed to prevent unittest from collecting imported test classes twice.

Syntax checks passed for all **288 Python files** discovered by `rg --files -g '*.py'`. Scoped `git diff --check` passed. SHA-256 comparison with the milestone backup confirmed `test_evidence_store.py` and `test_misconception_analyzer.py` were not changed.

No live Gemini calls, dependency installations, environment-file changes, commits or pushes were made. Automated UI tests used temporary SQLite databases and controlled semantic responses. Live semantic-review quality and manual browser behavior remain unverified.

## Streamlit acceptance checks

1. Open **Advanced Coding Agent → Personalized Practice** for an unassessed profile. Load Recursion: it should select the easy factorial task without increasing attempts.
2. For a profile whose actual assessments support medium or hard practice, load a new exercise and compare the recommended level with the loaded task. The task should change, not just its label.
3. Try Strings, Python Functions and Searching Algorithms. Request three hints and refresh; the exercise, code and hint progression should remain.
4. Submit a solution, refresh and submit identical code again. The saved assessment should be reused without another cognitive attempt. Switch profiles to verify isolation.
5. Use a solution that fails one predefined case. It should not be classified correct, even if semantic feedback is positive. A timeout should be reported explicitly.
6. Where genuine contradictory assessed evidence exists for an added topic, check that it appears in the diagnostic selector. General code review and AI corrections must not count as student mastery evidence.

Stop here for approval before Milestone 6 (Research Agent).
