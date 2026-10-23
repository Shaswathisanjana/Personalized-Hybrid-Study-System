# Unified query UI and orchestration refinement

The existing inline workspace was retained. This refinement makes its common
query the ordinary entry point, moves advanced controls behind optional debug
expanders, adds contextual clarification, and distinguishes saved-paper analysis
from academic search. No agent services or CACM scoring rules were replaced.

## Exact files modified

| File | Change |
| --- | --- |
| `review_ui.py` | Exact input label **What would you like help with today?**; advanced navigation/status inside collapsed Professor/Developer Debug expanders; natural **Your lesson** heading; saved clarification/reply/cancel flow without replacing prior work |
| `app/orchestrator/query_router.py` | Keep Gemini semantic routing and the existing local fallback; support validated clarification outcomes and search versus collection mode; minimum-context requests and ambiguous fallback requests ask for clarification |
| `app/orchestrator/study_workspace.py` | Retain validated research mode in the existing bounded saved plan, with old plans defaulting to search |
| `app/orchestrator/streamlit_workspace.py` | Keep real inline workflows; render PDF/mixed collection analysis for collection requests without starting academic retrieval; debug-only routing details |
| `app/orchestrator/streamlit_journey.py` | Put the optional shared-state policy/handoff panel behind a Professor/Developer Debug label in Student View; preserve advanced behavior |
| `app/coding_agent/streamlit_page.py` | Optional student-facing wording instead of internal agent decision labels; preserve advanced defaults, actual assessment and hint services |
| `app/research_agent/streamlit_page.py` | Place the internal research decision dashboard inside an optional debug expander when embedded in Student View |
| `app/persistence/session_recovery.py` | Persist and validate profile-owned pending clarification; preserve existing model, assessments and recovery |
| `app/persistence/state_codec.py` | Backward-compatible decoding of saved routes created before the optional research-mode field |
| `tools/browser_workspace_smoke.py` | Three representative queries, fresh-document reload assertions, content/settling checks and four screenshots using an isolated offline-backed real Chrome instance |
| `tools/offline_suite.json` | Add the new deterministic refinement module |
| `README.md` | Current 26-module suite count and this delivery report link |
| `docs/EVALUATION.md` | Current suite size and refinement coverage |

Created:

- `test_unified_query_refinement.py`
- `UNIFIED_QUERY_REFINEMENT_REPORT.md`

Backups are under `.milestone_backups/unified_refinement_20261020/`, with relative
paths preserved. The research-page backup reconstructs the small pre-edit block
after its initial copy failed; the other backups were copied before editing.
Existing unrelated/uncommitted work was retained. No reset, clean, commit, push,
dependency installation, Python environment change or mastery-rule change was made.

## Final student interface

The default Student View shows the study-assistant title, example requests,
one common **What would you like help with today?** input and **Start** button.
Students do not select an agent to submit a request. The profile selector selects
an identity, not an agent. Study plan, progress and topic browser remain available.

The actual activity appears below the common query:

- **Teach me recursion** opens the real lesson/resources and adaptive practice.
- **Give me a coding problem on linked lists** uses existing generation and
  executable package validation, then opens the editor, assessment, feedback and
  hints in the same Student View.
- **Find research papers about agentic AI** opens actual academic search and
  results, with selection, collections, analysis and reporting still available.
- **Compare my uploaded research papers** opens saved PDF/mixed collection
  extraction, analysis and comparison controls. It does not first search for
  unrelated papers. Analysis remains an explicit bounded action on selected
  sources; existing completed analysis is available for comparison.
- **Teach me recursion and then give me coding practice** retains the ordered
  bounded plan, pausing for student activity and using updated CACM when the
  next activity opens.

Routing explanation, advanced navigation, status panels and policy details are
inside optional **Professor/Developer Debug** expanders. The old technical lesson
heading is replaced by **Your lesson**. Advanced individual pages and Professor
Demo remain available, and explicit saved debug-view selections still recover.

When context is genuinely missing, semantic routing can request clarification.
The application saves the question under the current profile and asks the student
to clarify the task/topic in the same query input. It does not execute an unrelated
workflow or award mastery. Replies include the original request and prior topic
as context. Pending clarification survives refresh; cancellation returns to saved
prior work. No new probabilistic mastery model was introduced.

## Screenshots

These are actual headless Chrome screenshots of an isolated fixture-backed
application, not generated mockups or live-provider research findings:

- [Landing](data/browser_smoke/20261020T165850665812Z/landing.png)
- [Learning](data/browser_smoke/20261020T165850665812Z/learning.png)
- [Coding](data/browser_smoke/20261020T165850665812Z/coding.png)
- [Research](data/browser_smoke/20261020T165850665812Z/research.png)

## Actual checks executed

| Command/check | Result |
| --- | --- |
| `python -B tools/evaluate_offline.py` | **67/67 cases passed**: 26 unittest modules with **202 unittest executions**, plus **41 standalone script passes**; zero failures/errors/skips/timeouts |
| Final `python -B tools/evaluate_offline.py --only test_unified_query_refinement` | **11/11 tests passed**, including the final student-facing lesson-heading assertion |
| `python -B -m unittest tools.test_local_delivery tools.test_evaluate_offline` | **13/13 tooling tests passed** |
| Final `python -B tools/browser_workspace_smoke.py` | **30/30 browser checks passed** across the landing page, three representative queries, fresh-document reload, actual code assessment, persisted attempt count and screenshot readiness |
| `python -B run_phss.py --check` | Dependency import preflight passed; no provider calls or student data opened by this check |
| Syntax audit | **334 Python files** parsed successfully |
| Source/backup whitespace audit | No newly added trailing whitespace |
| Protected test hashes | Unchanged |

Full suite artifacts: `data/evaluation/20261020T165311535966Z/`.
Final focused artifacts: `data/evaluation/20261020T165623980744Z/`.
Final browser artifacts: `data/browser_smoke/20261020T165850665812Z/`.
Each directory retains its actual results/logs; the browser directory includes
screenshots and an isolated fixture DB/browser profile. Earlier development
attempts remain recorded; only the final successful executions are reported as
passes here. A standalone script pass is a successful process exit, not a unit
test. Browser checks include readiness/assertion checks, not thirty different
student scenarios. Historical tests outside the maintained manifest were not run.

The new tests run controlled provider responses through the real `QueryRouter`
parser and application services. They verify ordinary requests enter actual
workflows without manually selecting an agent, linked-list package execution,
adaptive answer assessment, seven search results, two real synthetic PDF files
being extracted/analyzed/compared without search, contextual clarification,
cross-profile rejection, old-route decoding, bounded sequencing and refresh
recovery. Synthetic fixture PDFs/results are not real academic publications.

The browser uses existing Chrome and installed dependencies, with a separate
localhost fixture server and database. It makes no live AI/provider calls and
does not use an existing personal browser profile. Its reload assertions wait
for a genuinely new document rather than matching stale pre-reload DOM text.

Protected SHA-256 values:

- `test_evidence_store.py`: `FC39C8DF1623202AC1570A5288B2823613D3E1200DD1761D25FCFFDCF113035C`
- `test_misconception_analyzer.py`: `6B0A9C6A75EA74F20F0EAFB5810188FBB18417429D2470D934A513D75BE07F68`

## Manual verification

1. Run `python -B run_phss.py` in the existing environment, select a profile and
   use Student View. Expand Professor/Developer Debug only for expert navigation.
2. Submit each example above through the same common input. Confirm the actual
   lesson, editor or research controls appear without changing pages manually.
3. Ask an ambiguous request, refresh, then clarify it in the same input. Confirm
   that pending clarification adds no assessed attempts and prior work remains.
4. Refresh an active learning/coding/research activity using the same profile URL.
   Resubmitting already assessed identical code must not increment attempts twice.
5. With saved PDFs, request comparison, extract/analyze selected bounded batches,
   and inspect page/chunk evidence. No unrelated paper search should occur.
6. Switch profiles and return to check isolation. Existing assessment recovery,
   source coverage, duplicate protection and real-conflict diagnostics remain.

## Remaining limitations

- Live Gemini interpretation/clarification quality and academic-provider relevance
  were not evaluated. Fixtures establish software behavior, not universal natural-
  language accuracy, calibrated mastery or real-student learning gains.
- The existing local fallback is conservative and less capable than semantic
  routing; unsupported or underspecified requests can require clarification.
- Plans remain bounded to up to three distinct activities for the shared topic.
  This refinement does not add a general multi-topic/repeated-agent planner.
- Collection processing still needs explicit source selection and bounded actions;
  opening it is not a claim that every saved PDF was already analyzed.
- Existing searches and matching work are retained rather than silently replaced.
  Provider-dependent initial preparation can fail and needs explicit retry.
- Explicit advanced debug views remain recoverable; normal fresh profiles default
  to Student View. No ordinary workflow requires choosing an advanced agent page.
- Existing Python-only execution, local subprocess security, profile-ID authentication
  limitations, OCR absence, native Word/download coverage and production-load
  boundaries remain unchanged. No environment or production deployment work was done.

This completes the requested refinement. No further phase was started.
