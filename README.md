# CACM-PHSS

Cross-Agent Cognitive Modeling for a Personalized Hybrid Study System. This final-year prototype connects Learning, Coding and Research agents through one evidence-driven student model and a Streamlit application.

The agents adapt their next activity from assessed work. CACM records evidence, updates mastery and misconception hypotheses, detects disagreement between agents, and uses diagnostics to resolve it. Reading a lesson or opening a paper does not demonstrate mastery.

- **Learning:** 50 topics plus custom topics, real resources, adaptive 5/10/15/20-question practice, prerequisite-aware plans, revision and saved history.
- **Coding:** 18 curated exercises plus free-text Python topics with generated packages checked against actual subprocess tests, CACM-selected difficulty, original-code assessment, saved hints and verified correction review. See [open-topic coding](docs/OPEN_TOPIC_CODING.md) for coverage and execution limits.
- **Research:** OpenAlex topic search with incremental retrieval and persistent selection, abstract quality checks, resumable analysis and comprehension assessment. Student-owned PDF collections support page-cited extractive analysis. Mixed PDF/abstract collections support selectable Word reports while retaining the existing Markdown export; see [research search and Word reports](docs/RESEARCH_SEARCH_AND_DOCX.md).
- **Study workspace:** one query opens real learning, coding and research activities inline, with a saved multi-step sequence, automatic initial preparation, shared recommendations and genuine-conflict diagnostics. SQLite profiles restore cognitive state and unfinished work after refresh. See [the unified workspace guide](docs/UNIFIED_STUDY_WORKSPACE.md).

These features have controlled offline checks. Live provider quality, deployment security and educational effectiveness require separate validation.

## Run

See [setup](docs/SETUP.md) for the existing environment and provider configuration. From a configured environment at the project root:

```powershell
python -B run_phss.py --check
python -B run_phss.py
```

The separate Node/MongoDB prototype is not required by this Python application.

The launcher uses existing installed packages, binds to `127.0.0.1` and disables Streamlit usage telemetry. It does not install packages. `requirements.txt` records the observed direct dependency versions; a clean installation remains unverified.

Create a consistent local student-data backup without overwriting an existing file:

```powershell
python -B tools/backup_student_data.py
```

## Evaluate

```powershell
python -B tools/evaluate_offline.py
```

The maintained manifest selects 26 unittest modules and 41 standalone scripts, including unified workspace, open-topic coding, PDF collection, academic search and DOCX checks. Results, logs and an inventory of other root tests are saved to ignored `data/evaluation/<UTC timestamp>/`. This command does not install packages or intentionally contact live APIs. Read the [evaluation protocol](docs/EVALUATION.md) before interpreting results.

## Project guide

- [Architecture and data flow](docs/ARCHITECTURE.md)
- [Setup and refresh recovery](docs/SETUP.md)
- [Evaluation and acceptance scenarios](docs/EVALUATION.md)
- [Methodology and defensible claims](docs/METHODOLOGY.md)
- [Limitations and remaining priorities](docs/LIMITATIONS.md)
- [Presentation and demonstration guide](docs/DEMO_AND_VIVA.md)
- [Phases 5–6 completion and acceptance report](PHASES_5_6_COMPLETION_REPORT.md)
- [Unified landing and clarification refinement](UNIFIED_QUERY_REFINEMENT_REPORT.md)
- [Final local delivery report](FINAL_DELIVERY_REPORT.md)

Milestone reports 4–8 record implementation scope, checks and limitations. This is a local research prototype: profile identifiers are not authentication and the code runner is not a security sandbox. Use trusted code in the current local deployment.
