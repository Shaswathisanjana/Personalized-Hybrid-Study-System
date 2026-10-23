# Milestone 6: Research Agent

Implemented on 20 October 2026 in the existing PHSS application. Milestone 7 has not begun.

## Delivered behavior

- **Paper counts are targets.** Planned retrieval now pursues the requested number of usable publications rather than stopping at two. It uses the existing bounded planned-query search. Counts, rejected abstracts, overlapping results and provider warnings explain shortfalls. No sources or findings are invented to fill a quota.
- **Conservative publication identity.** Matching publication IDs or normalized DOI URLs can identify duplicates. Generic URLs additionally require matching titles, since a shared landing page can represent different publications. A retrieved duplicate with a usable abstract can replace an earlier unusable record. Different publications remain separate.
- **Recoverable content analysis.** A student-scoped research job saves its request, plan, retrieved sources, successful summaries and completed downstream stages. Each source summary is checkpointed separately. Refresh does not automatically invoke providers; explicit Retry unfinished research analysis resumes work.
- **Partial failures preserve success.** Summary failures are recorded per source. Successful summaries are reused. A partly failed retrieval retries failed planned queries using the existing source pool. Completed thematic/comparison/opportunity/proposal stages are reused unless the summary set changes, in which case dependent analysis is regenerated.
- **Traceable evidence.** The UI and Markdown export include the requested target, retrieved publication metadata and unfinished stages alongside the existing quotations, source links, abstract-quality decisions and evidence limitations. Summary identity must match its retrieved source. Quotes must occur in that abstract; fields without quotes remain Not reported in available source. Source metadata comes from the retrieved record.
- **Genuine diagnostics remain accessible.** The Research page can display actual unresolved CACM conflicts even before generating a new research report. It renders one diagnostic interface, retains completed feedback, and protects the selected topic of an active diagnostic across refresh when several conflicts exist.
- **Content is not mastery evidence.** Planning, retrieval, summarization, report downloads and retries create no assessment evidence. Only the existing evaluated comprehension and diagnostic answer workflows update CACM.

## Compatibility and limits

The current ResearchWorkflowResult data class gains four optional recovery fields. Explicit decoder defaults support old saved results, including still-running instances missing the new fields. Unknown snapshot fields remain rejected. Existing saved reports remain viewable; a historical report without a saved job/request does not gain an invented resumable request. No SQLite table change was needed.

The production summarizer runs per paper. Existing injected batch-only summarizers are still supported; they cannot expose an individual successful result until their batch returns. Successfully checkpointed output is reused. A provider operation interrupted before its output is saved may need another call on explicit retry; exact-once external billing is not guaranteed.

OpenAlex remains the existing academic retrieval provider. Search is bounded by the existing planned queries and attempt cap. A completed bounded search may return fewer usable publications than requested. Abstract-quality checks are heuristics about available text, not judgments of a publication's academic merit. Quote membership provides traceability but does not independently prove that an interpretation follows from its quote. Analysis remains abstract-only and proposed opportunities require broader literature verification.

No live provider calls were made during implementation. Current OpenAlex availability, Gemini output quality and a manual browser session remain unverified. All new automated publication records are clearly identified fixtures using reserved example.org URLs. No dependency installation, credential/environment edit, commit or push was performed.

## Exact files created or modified

| Status | File | Purpose |
| --- | --- | --- |
| Created | `app/research_agent/source_identity.py` | Conservative deduplication and exact-source cache fingerprints |
| Created | `app/research_agent/analysis_execution.py` | Checkpointed retrieval, summary and downstream analysis stages |
| Created | `app/research_agent/analysis_recovery.py` | Student-scoped analysis job execution and explicit recovery |
| Created | `test_research_analysis_recovery.py` | Sixteen deterministic source, grounding, retry and compatibility tests |
| Created | `test_research_analysis_streamlit.py` | Five main-app research/diagnostic recovery and isolation tests |
| Modified | `app/research_agent/autonomous_search.py` | Count usable unique sources; seed retries with existing publications |
| Modified | `app/research_agent/research_workflow.py` | Recovery metadata and delegation through the existing workflow API |
| Modified | `app/research_agent/personalized_coordinator.py` | Preserve the plan and expose content checkpoints |
| Modified | `app/research_agent/streamlit_page.py` | Saved job, explicit retry and one genuine diagnostic interface |
| Modified | `app/research_agent/streamlit_results.py` | Requested target, source records and unfinished-stage display |
| Modified | `app/research_agent/report_exporter.py` | Requested target, source manifest and unfinished-stage export |
| Modified | `app/persistence/session_recovery.py` | Persist analysis jobs within the selected student profile |
| Modified | `app/persistence/state_codec.py` | Explicit legacy defaults for the four new result fields |
| Modified | `test_personalized_research_coordinator.py` | Correct assessed/unassessed fixtures and require genuine conflict evidence |
| Modified | `test_research_diagnostic_ui_integration.py` | AST checks for a single diagnostic call and completed-feedback state |

This report is also new. Originals and the local offline regression harness are in `.milestone_backups/milestone6_20261020/` (ignored by Git). Both protected uncommitted tests, `test_evidence_store.py` and `test_misconception_analyzer.py`, match their pre-milestone SHA-256 hashes. Other existing uncommitted work was preserved.

## Verification

**108 distinct unittest tests passed**: 87 earlier tests and 21 new research tests. The combined batch passed 107 tests; the final focused batch passed 21 after adding one additional stale-warning regression. The overlap is intentional.

Combined batch actually executed:

```powershell
python -B -c "import sys; sys.path.insert(0,'.venv/Lib/site-packages'); import unittest; unittest.main(module=None, argv=['unittest','test_research_analysis_recovery','test_research_analysis_streamlit','test_verified_coding_catalog','test_coding_practice_streamlit','test_learning_study_planner','test_learning_study_plan_streamlit','test_assessment_transactions','test_assessment_transactions_streamlit','test_concept_identity','test_concept_migration','test_student_persistence','test_assessment_recovery','test_persistence_streamlit'], verbosity=1)"
```

Final focused batch actually executed:

```powershell
python -B -c "import sys; sys.path.insert(0,'.venv/Lib/site-packages'); import unittest; unittest.main(module=None, argv=['unittest','test_research_analysis_recovery','test_research_analysis_streamlit'], verbosity=1)"
```

New tests exercise requested-count refinement, rejected/duplicate sources, richer abstracts, generic shared URLs, DOI normalization, partial retrieval recovery, source-only retry, failed thematic-stage retry, empty supplied input without network, rejected invented quotes, unquoted claims, strict legacy defaults, durable interruption/reload, profile isolation and genuine diagnostic resolution without generating research first. Viewing and retrying content leave CACM attempts and evidence unchanged.

Standalone regression command:

```powershell
python -B .milestone_backups/milestone6_20261020/run_offline_checks.py
```

All **41 scripts passed** in the final run: the earlier 29 regressions plus abstract validation, autonomous research search/end-to-end refinement, coordinator/planner integration, report export/exclusions, filtering, assessment context, opportunities and objectives. External socket connections are blocked while Windows loopback connections remain allowed for Streamlit.

The first broad run passed 38/41 scripts. Investigation established:

1. The personalization test already failed against the backed-up pre-milestone coordinator: it expected assessed behavior from zero attempts and later requested a fabricated conflict. Its fixture now represents assessed low mastery, separately checks an unassessed profile, rejects an unsupported conflict flag and verifies actual contradictory observations. Content generation must leave the resulting cognitive state unchanged.
2. The diagnostic integration test depended on exact indentation and quote characters. AST checks now preserve its actual requirements: exactly one diagnostic call and access to the completed-feedback session key. Other checks remain intact.
3. Filtering fixtures used one generic URL for three differently titled publications. Conservative generic-URL/title identity preserves them, allowing the existing exclusion assertions to pass. A dedicated new regression covers this case.

All **293 Python files** discovered by `rg --files -g '*.py'` passed syntax parsing. Scoped `git diff --check` passed. Protected-file hash checks passed. The dependency directory was used through a process-local sys.path insertion, without changing the environment.

## Manual Streamlit acceptance

1. Open Advanced Research Agent, enter a topic and learning concept, and request 3–5 papers. Compare the target, retrieved, accepted, excluded and summarized counts. A shortfall must be explained.
2. Inspect Retrieved source records, excluded-paper reasons, supporting quotations and the Markdown report's source manifest. Unknown details should stay Not reported.
3. If a provider stage fails, refresh and use Retry unfinished research analysis. Successful summaries should remain; retrying content should not increase cognitive attempts.
4. Switch student profiles and verify that saved requests, source records and completed analysis stay with their owners.
5. When actual contradictory assessments create a conflict, use the diagnostic selector without first generating a report. Refresh an active diagnostic and verify its topic/question remain. Submit an answer and verify retained feedback and CACM resolution behavior.

Stop here for approval before Milestone 7: unified three-agent student journey.
