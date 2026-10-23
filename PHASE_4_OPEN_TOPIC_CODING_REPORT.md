# Phase 4 — Open-topic Coding Agent

Implemented Phase 4 only, continuing the existing application and Phase 3 work.
Phases 5 and 6 have not been implemented. No commits, staging, pushes, resets,
cleanup, dependency installation or Python environment changes were performed.
Existing uncommitted work was preserved.

## Exact source/documentation changes

Created five files:

1. `app/coding_agent/open_topic.py`
2. `test_open_topic_coding.py`
3. `test_open_topic_coding_streamlit.py`
4. `docs/OPEN_TOPIC_CODING.md`
5. `PHASE_4_OPEN_TOPIC_CODING_REPORT.md`

Modified eleven existing files, relative to the start of Phase 4:

1. `app/coding_agent/progressive_hint_engine.py` — use generated task-specific hints while preserving the curated bank.
2. `app/coding_agent/submission_controller.py` — incorporate generated package identity in assessment IDs; keep existing curated receipt IDs compatible.
3. `app/coding_agent/streamlit_page.py` — topic/language inputs, bounded validated generation, durable draft handling, existing submission/hint integration, correction review/verification, and progress for assessed custom topics.
4. `app/coding_agent/streamlit_diagnostic.py` — include genuine conflicts for custom concepts in the existing diagnostic selector.
5. `app/persistence/state_codec.py` — allowlist the two new data classes.
6. `app/persistence/session_recovery.py` — persist custom-topic inputs, language, attempt bound, generation status and guided review results.
7. `review_ui.py` — preserve coding widget drafts when navigating to another page, after owner-scoped profile loading.
8. `tools/offline_suite.json` — add the two new offline test modules.
9. `README.md` — describe open-topic coding and the expanded maintained suite.
10. `docs/EVALUATION.md` — document the 23-module suite and new coverage.
11. `docs/LIMITATIONS.md` — replace the obsolete claim that arbitrary-topic practice is unsupported with the actual Python and validation boundaries.

Pre-edit copies are in `.milestone_backups/phase4_open_coding_20261020/`,
preserving relative paths. This includes an unchanged backup of
`tools/evaluate_offline.py`; that runner was **not modified**. Evaluation runs
also created ignored logs/metrics in the artifact directories listed below.
There is no database schema or dependency manifest change in Phase 4.

## Implemented behavior and reused modules

- The exact requested **What coding topic would you like to practise?** input
  accepts free text; a blank input keeps the existing curated selector.
- Concept normalization reuses the existing conservative CACM identity rules.
  It does not merge vaguely related algorithms or languages.
- Recommendation preview reads the existing Coding Agent policy on a copy of
  the shared student model, with genuine conflict information from CACM.
  This avoids creating cognitive state while browsing or generating.
- The existing `CodingTaskGenerator` Gemini client/model architecture generates
  JSON packages with a statement, input/output contract, constraints, examples,
  starter, reference solution, tests and three hints. The generator is injected
  with deterministic providers in offline tests.
- Validation checks package size/shape, Python syntax, the required function,
  exact recommended difficulty, distinct test inputs, valid tested example
  references and obvious prohibited host-access operations. It then uses the
  existing `ControlledCodeRunner` to execute the reference, unfinished starter
  and a constant-None probe. A package is accepted only after the reference
  passes every supplied test and both incomplete implementations are rejected.
- Limits are visible: 1–3 attempts (default 2), 3–8 tests, five seconds per
  validation subprocess, and a 30-second provider HTTP timeout with SDK retries
  disabled. Package, topic, output-token and per-test data limits also apply;
  see the manual guide for exact values and deadline limitations.
- The original 18 curated exercises remain available without generation.
  Failed/interrupted custom generation leaves the previous package and draft
  saved, reports failure honestly, and requires explicit retry.
- Native SQL, JavaScript, Java and C++ execution is explicitly unsupported.
  Selecting one hides generation and submission controls instead of claiming
  the code ran. Python is the supported local execution environment.
- `CodingSubmissionController`, `IntegratedCodingWorkflow`, `CodingEvaluator`
  and the existing CACM runtime assess the student's original code. Objective
  test failures cannot be replaced by a favorable semantic score. Generated
  packages have distinct IDs to prevent collisions across different test sets.
- Existing progressive/adaptive hint coordination works with generated hints;
  unsupported static misconception patterns are not invented. Existing semantic
  evaluation can report misconceptions supported by the assessed code.
- After an assessment, `GuidedCodeReviewCoordinator` and `CorrectionVerifier`
  provide a separate, optional AI correction and its actual supplied-test
  status. Viewing, hinting, generating and verifying corrections add no mastery.
- SQLite snapshot recovery restores accepted packages, editor drafts, hints,
  reviews and assessment receipts. Runtime services are rebuilt using the
  existing profile-bound recovery mechanism. Profile switching clears the
  previous owner's inputs and work. No independent learner model was added.
- Original-code evidence drives subsequent recommendations and the existing
  genuine-conflict diagnostics. Assessed custom topics are included in coding
  progress and diagnostic selection; no synthetic conflicts are introduced in
  the normal UI.

Learning, research PDF/search/analysis/DOCX/Markdown, persistence and CACM modules
were retained. Their maintained offline cases passed in the run below.
Unified autonomous query routing remains Phase 5 work.

## Actual verification results

| Executed check | Actual result |
| --- | --- |
| `python -B tools/evaluate_offline.py` | **63/64 cases passed**: all 23 unittest modules passed with **178 unittest executions**, zero failures/errors/skips; 40/41 standalone scripts passed, and `test_learning_topic_bank.py` timed out |
| `python -B tools/evaluate_offline.py --only test_learning_topic_bank.py` | **1/1 passed**, without changing that script or its dependencies; this is a script exit, not a unit-test count |
| `python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline` | **13/13 tooling tests passed** |
| Syntax parsing of root, `app/` and `tools/` Python sources | **328 files parsed successfully** |
| `python -B run_phss.py --check` | Passed dependency import checks; no live providers called or student data opened |
| Protected test hashes | Unchanged for `test_evidence_store.py` and `test_misconception_analyzer.py` |
| Whitespace audit | No added trailing whitespace relative to Phase 4 backups; repository-wide `git diff --check` still reports the pre-existing unrelated EOF/trailing-whitespace issues |

The full-run artifact is
`data/evaluation/20261020T112843334394Z/` (`results.json`, `summary.md`, case logs
and unittest metrics). The isolated topic-bank rerun artifact is
`data/evaluation/20261020T122354092360Z/`.

**The full run itself was not a clean 64/64 pass.** The topic-bank timeout did
not reproduce on its isolated rerun; its root cause was not established. All
selected cases have a passing execution across the full run and rerun, but
that does not erase the timeout in the original record.

New tests in the full run comprise **16 backend tests and 4 Streamlit tests**.
They cover executable merge/BST/decorator fixtures, real reference and probe
validation, wrong expected outputs, completed starters, invalid packages,
nontermination rejection, conservative normalization, CACM-selected difficulty,
bounded provider failures, secret-safe errors, unsupported languages, distinct
package receipts, hint progression, correction verification, refresh/navigation,
profile isolation, original failing-code assessment, duplicate resubmission and
custom-topic genuine conflict visibility. No live model outcomes were faked as
executed live tests.

Development runs caught and fixed hidden-editor draft cleanup and rejection of
valid code under an overly short validation timeout. A deliberately failing
student-code UI test also needed to distinguish expected failed-test feedback
from application errors. The retained targeted artifacts
`data/evaluation/20261020T112703655720Z/` (failed expectation) and
`data/evaluation/20261020T112747904446Z/` (three tests passed before the fourth
conflict test was added) record that development sequence. The final full run
contains all four UI tests passing.

Protected SHA-256 values:

- `test_evidence_store.py`: `FC39C8DF1623202AC1570A5288B2823613D3E1200DD1761D25FCFFDCF113035C`
- `test_misconception_analyzer.py`: `6B0A9C6A75EA74F20F0EAFB5810188FBB18417429D2470D934A513D75BE07F68`

## Limitations and unverified work

- Live Gemini generation/review quality, costs, latency and availability have
  not been tested. No paid provider calls were made during verification.
- Supplied tests and reference solutions are generated together. Passing proves
  agreement with those tests, not independent correctness, topic relevance,
  complete coverage, complexity compliance or educational quality. The UI and
  guide state this explicitly.
- Generated practice supports dependency-free Python functions with JSON inputs
  and return values. Unsupported native runtimes, external packages, imports,
  interactive/GUI programs and arbitrary project execution remain out of scope.
- AST checks are defense in depth, not isolation. The existing subprocess runner
  has local user filesystem/network permissions and no memory/output quota;
  this phase does not make hostile code safe to run.
- Per-request/per-test timeouts and bounded attempts do not give a hard OS-level
  deadline for the entire workflow. Slow machines may need several minutes.
- A process crash after a provider response but before a checkpoint can require
  another generation call on explicit retry; exactly-once provider billing is
  not guaranteed. Accepted packages and previous work do persist.
- Handwritten misconception detectors still cover their original topics;
  arbitrary topics use generated hints and the existing semantic assessment.
- AppTest exercised the actual main page offline. A live browser/model walkthrough
  and broad browser/accessibility/load testing were not performed. UUID profile
  separation remains local ownership isolation, not authentication.
- The isolated topic-bank pass does not explain its full-run timeout. Other
  historical tests outside the maintained manifest were not executed.

## Manual Streamlit verification and stop point

Follow [the open-topic coding guide](docs/OPEN_TOPIC_CODING.md). Start with a
curated exercise, then load a custom Python topic, inspect the coverage label,
request hints, refresh, submit incorrect original code and inspect failed cases.
Request correction verification, confirm mastery does not change from review,
and resubmit identical original code to check duplicate protection. Test a
provider failure, select unsupported SQL, navigate away/back and switch student
profiles. Keep the same profile URL for refresh recovery.

**Phase 4 is delivered with the verification boundaries above. Stop here and
wait for approval before Phase 5.**
