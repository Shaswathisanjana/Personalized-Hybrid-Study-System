# Milestone 8: Evaluation and final-year deliverables

Implemented on 20 October 2026 in the existing PHSS project. This milestone adds evaluation tooling and documentation; it does not change agent, cognitive, persistence or application behavior.

## Files

| Status | File | Purpose |
| --- | --- | --- |
| Modified | `README.md` | Project capabilities, entry point, evaluation command and guide |
| Modified | `.gitignore` | Ignore local evaluation results/logs |
| Created | `tools/evaluate_offline.py` | Explicit offline suite execution, per-case bounds, logs, counts, hashes and reports |
| Created | `tools/offline_suite.json` | Curated 15 unittest modules and 41 standalone regression scripts |
| Created | `tools/test_evaluate_offline.py` | Seven infrastructure checks using disposable real subprocesses |
| Created | `docs/ARCHITECTURE.md` | Agent responsibilities, shared-state communication, UI/provider connections and refresh recovery |
| Created | `docs/SETUP.md` | Observed environment, normal/fallback startup, provider names and data handling |
| Created | `docs/EVALUATION.md` | Reproducible commands, acceptance mapping, controlled scenario and evidence boundaries |
| Created | `docs/METHODOLOGY.md` | Engineering method, implemented score/conflict rules and defensible claims |
| Created | `docs/LIMITATIONS.md` | Current boundaries and prioritized remaining work |
| Created | `docs/DEMO_AND_VIVA.md` | Slide outline, offline demonstration, manual browser checklist and viva answers |
| Created | `MILESTONE_8_REPORT.md` | Scope, verification and limitations |

Existing README and ignore rules were backed up before editing in `.milestone_backups/milestone8_20261020/`. Only one evaluation-output ignore entry was appended to existing rules. No historical tests were overwritten or reclassified as live successes.

## Evaluation behavior

The standard-library parent runner launches each explicit case separately with the current interpreter and optional local package fallback. Children use dummy process-local provider keys and block non-loopback TCP connects. Loopback remains allowed for Streamlit AppTest. This is an accidental-network guard for reviewed tests, not hostile-code isolation.

The runner fails on unsuccessful child exits, missing files, empty unittest suites, missing unittest metrics and timeouts. It reports unittest counts separately from standalone script exits and records skips. Per-case source hashes, a manifest hash, runtime information, logs, durations and root test inventory are saved to ignored timestamped `data/evaluation/` folders. Unselected root tests are explicitly `not_run`, not passed. A selected case run is labelled separately from the full curated suite.

Seven new infrastructure checks verify success, failed assertions, zero-test suites, nonzero scripts, missing cases, timeout and rejected external connections. Their fixtures contain no provider calls or app data.

## Commands and results

```powershell
python -B tools/evaluate_offline.py --list
python -B tools/evaluate_offline.py --only test_student_journey
python -B tools/evaluate_offline.py
python -B -m unittest tools.test_evaluate_offline
git diff --check -- README.md .gitignore
```

The full command passed **56/56 cases**: **120 application unittest executions across 15 modules, zero failures/errors/skips, and 41 standalone script passes**. The separate runner infrastructure command passed **7/7 tests**. There were no failed, missing or timed-out cases in the full curated run.

Full artifacts: `data/evaluation/20261020T080401757512Z/summary.md` and `results.json`, with individual logs. The selected preliminary journey run is separately recorded at `data/evaluation/20261020T080147293960Z/` and is not added again to the 120-test application count. Other historical root tests remain unexecuted by this suite and are listed as `not_run` in the inventory.

The initial selected journey run passed seven tests. The infrastructure command passed seven tests, including intentional failure fixtures that the runner correctly reported as failures. Syntax parsing passed all 299 application/root/tool Python files. AST import inspection confirmed the documented third-party roots (`dotenv`, `google`, `streamlit`). All local Markdown links in the README/docs resolved.

The scoped whitespace check passed. A broader `git diff --check` found existing trailing whitespace/EOF warnings in `app/learning_agent/resources/resource_recommender.py` and protected `test_evidence_store.py`; those files were not changed in this milestone. Protected test SHA256 values remain:

- `test_evidence_store.py`: `FC39C8DF1623202AC1570A5288B2823613D3E1200DD1761D25FCFFDCF113035C`
- `test_misconception_analyzer.py`: `6B0A9C6A75EA74F20F0EAFB5810188FBB18417429D2470D934A513D75BE07F68`

## Manual verification and limitations

Follow `docs/DEMO_AND_VIVA.md` using a disposable profile: assess a topic, refresh the same profile URL, switch workflows with an unfinished quiz/code draft, inspect research inputs, and verify separation from a second profile. Live generation/submission and provider quality checks were not performed in this milestone. They require configured providers and separate authorization/budget. A manual browser session was not substituted for AppTest or claimed as completed.

The environment has installed packages but lacks `.venv/Scripts/python.exe`; the process-local fallback is documented. No clean environment installation or dependency lock was validated. No packages, environment files, secrets or real student databases were modified. No commit, staging or push occurred.

The project now has a documented, reproducible prototype evaluation path. It does not establish real-student learning improvement, calibrated mastery probabilities, a systematic literature review, public deployment security or live-service reliability. Before public use, prioritize authenticated authorization and isolated code execution. For local delivery, prioritize an approved clean-environment setup check and manual demonstration; then plan live-provider quality checks and a separate educational study.
