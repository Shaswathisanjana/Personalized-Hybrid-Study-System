"""Deterministic source/retry/legacy-snapshot checks; publications are fixtures."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from app.research_agent.models import ResearchPaper
from app.research_agent.paper_summarizer import PaperSummary, NOT_REPORTED
from app.research_agent.research_workflow import IntegratedResearchWorkflow, ResearchWorkflowResult
from app.research_agent.autonomous_search import AutonomousResearchSearcher
from app.research_agent.personalized_coordinator import PersonalizedResearchCoordinator
from app.research_agent.analysis_recovery import run_analysis_job
from app.research_agent.report_exporter import ResearchReportExporter
from app.research_agent.source_identity import merge_sources
from app.research_agent.abstract_quality_validator import AbstractQualityValidator
from app.research_agent.thematic_reviewer import ThematicReview
from app.persistence.state_codec import encode, decode
from app.persistence.session_recovery import capture, restore
from app.persistence.sqlite_store import SQLiteStudentStore
from test_student_persistence import student_state
from test_persistence_streamlit import OfflineOrchestrator


METHOD = "We compare supervised classification methods."
ABSTRACT = ("This controlled synthetic abstract describes an experimental study of classification approaches. "
            + METHOD + " The authors explain the evaluation procedure and training data preparation, "
            "discuss measured outcomes in the available sample, and describe limitations concerning "
            "generalization beyond the original research setting. Additional independent evaluations "
            "are needed before broader conclusions can be drawn from this illustrative source.")


def paper(identifier, abstract=ABSTRACT):
    return ResearchPaper("Controlled study " + identifier, ["Fixture Author"], abstract,
                         "https://example.org/fixture/" + identifier, 2025, "offline_fixture", identifier)


class FixtureSummarizer:
    def __init__(self, failures=()):
        self.failures, self.calls = set(failures), []

    def summarize(self, source):
        self.calls.append(source.paper_id)
        if source.paper_id in self.failures:
            raise RuntimeError("Controlled summary outage")
        return PaperSummary(source.title, source.authors, source.year, source.url,
                            proposed_method=METHOD, evidence_quotes={"proposed_method": METHOD})


class FixtureSearch:
    def __init__(self, batches):
        self.batches, self.calls = batches, []

    def search(self, query, limit=5):
        self.calls.append((query, limit))
        value = self.batches[min(len(self.calls)-1, len(self.batches)-1)]
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(papers=deepcopy(value), provider_errors=[])


class ResearchRecoveryTests(unittest.TestCase):
    def test_search_pursues_requested_count_instead_of_stopping_at_two(self):
        search = FixtureSearch([[paper("a"), paper("b")], [paper("b"), paper("c")]])
        workflow = IntegratedResearchWorkflow(search, FixtureSummarizer())
        result = workflow.run("Controlled topic", 3, search_queries=["first", "second"], include_thematic_review=False)
        self.assertEqual(len(search.calls), 2)
        self.assertEqual(len(result.summaries), 3)
        self.assertEqual(result.requested_papers, 3)

    def test_duplicates_and_rejected_abstracts_do_not_satisfy_target(self):
        search = FixtureSearch([[paper("a"), paper("bad", "")], [paper("a")]])
        result = IntegratedResearchWorkflow(search, FixtureSummarizer()).run(
            "Controlled topic", 3, search_queries=["first", "second"], include_thematic_review=False)
        self.assertEqual(len(result.papers), 2)
        self.assertEqual(len(result.excluded_papers), 1)
        self.assertEqual(len(result.summaries), 1)
        self.assertTrue(any("1/3" in warning for warning in result.warnings))
        report = ResearchReportExporter.build_markdown(result)
        self.assertIn("Requested usable-paper target", report)
        self.assertIn("Controlled study bad", report)
        self.assertIn("offline_fixture", report)
        self.assertIn("https://example.org/fixture/a", report)

    def test_duplicate_with_richer_abstract_replaces_unusable_record(self):
        search = FixtureSearch([[paper("a", "")], [paper("a")]])
        result = AutonomousResearchSearcher(search).search(["first", "second"], target_usable_papers=1)
        self.assertEqual(len(result.papers), 1)
        self.assertTrue(result.target_reached)
        self.assertEqual(result.papers[0].abstract, ABSTRACT)

    def test_doi_normalization_and_distinct_publications(self):
        a, b = paper("a"), paper("b")
        a.url, b.url = "http://dx.doi.org/10.1234/ABC", "https://doi.org/10.1234/abc"
        self.assertEqual(len(merge_sources([], [a, b], AbstractQualityValidator())), 1)
        b.url = "https://doi.org/10.1234/different"
        b.title = a.title
        self.assertEqual(len(merge_sources([], [a, b], AbstractQualityValidator())), 2)

    def test_distinct_titles_on_generic_shared_url_are_not_merged(self):
        a, b = paper("a"), paper("b")
        a.url = b.url = "https://example.org/generic-page"
        self.assertEqual(len(merge_sources([], [a, b], AbstractQualityValidator())), 2)

    def test_partial_summary_failure_retries_only_failed_source(self):
        summarizer = FixtureSummarizer(["b"])
        workflow = IntegratedResearchWorkflow(summarizer=summarizer)
        result = workflow.run("Controlled topic", 2, papers=[paper("a"), paper("b")], include_thematic_review=False)
        self.assertEqual(len(result.summaries), 1)
        self.assertTrue(result.stage_errors)
        summarizer.failures.clear()
        workflow.run("Controlled topic", 2, include_thematic_review=False, resume_result=result)
        self.assertEqual(summarizer.calls, ["a", "b", "b"])
        self.assertEqual(len(result.summaries), 2)
        self.assertEqual(result.stage_errors, {})
        self.assertEqual(len(result.comparison.papers), 2)

    def test_thematic_retry_reuses_all_summaries_and_other_successful_stages(self):
        calls = []
        def review(topic, summaries):
            calls.append(topic)
            if len(calls) == 1:
                raise RuntimeError("Controlled thematic outage")
            return ThematicReview(topic, papers_analyzed=len(summaries))
        summarizer = FixtureSummarizer()
        workflow = IntegratedResearchWorkflow(summarizer=summarizer,
                    thematic_reviewer=SimpleNamespace(review=review))
        result = workflow.run("Controlled topic", 2, papers=[paper("a"), paper("b")])
        comparison = result.comparison
        self.assertIn("thematic_review", result.stage_errors)
        workflow.run("Controlled topic", 2, resume_result=result)
        self.assertEqual(summarizer.calls, ["a", "b"])
        self.assertIs(result.comparison, comparison)
        self.assertEqual(result.stage_errors, {})
        self.assertFalse(any("thematic outage" in w for w in result.warnings))

    def test_failed_retrieval_can_be_retried_without_fabricated_results(self):
        search = FixtureSearch([RuntimeError("Controlled retrieval outage"), [paper("a")]])
        workflow = IntegratedResearchWorkflow(search, FixtureSummarizer())
        result = workflow.run("Controlled topic", 1, include_thematic_review=False)
        self.assertFalse(result.search_complete)
        self.assertEqual(result.papers, [])
        workflow.run("Controlled topic", 1, resume_result=result, include_thematic_review=False)
        self.assertTrue(result.search_complete)
        self.assertEqual(len(result.summaries), 1)

    def test_partial_retrieval_retry_keeps_successes_and_only_repeats_failed_query(self):
        search = FixtureSearch([[paper("a")], RuntimeError("Controlled second-query outage"), [paper("b")]])
        summarizer = FixtureSummarizer()
        workflow = IntegratedResearchWorkflow(search, summarizer)
        result = workflow.run("Controlled topic", 2, search_queries=["first", "second"], include_thematic_review=False)
        self.assertEqual(len(result.summaries), 1)
        self.assertIn("search", result.stage_errors)
        workflow.run("Controlled topic", 2, search_queries=["first", "second"], resume_result=result,
                     include_thematic_review=False)
        self.assertEqual([q for q, _ in search.calls], ["first", "second", "second"])
        self.assertEqual(summarizer.calls, ["a", "b"])
        self.assertEqual(len(result.summaries), 2)
        self.assertEqual(result.stage_errors, {})
        self.assertFalse(any(w.startswith("Paper target not met") for w in result.warnings))

    def test_recovered_abstract_removes_obsolete_exclusion_warnings(self):
        search = FixtureSearch([[paper("a", "")], RuntimeError("Controlled outage"), [paper("a")]])
        workflow = IntegratedResearchWorkflow(search, FixtureSummarizer())
        result = workflow.run("Controlled topic", 1, search_queries=["first", "second"], include_thematic_review=False)
        self.assertEqual(len(result.excluded_papers), 1)
        workflow.run("Controlled topic", 1, search_queries=["first", "second"], resume_result=result,
                     include_thematic_review=False)
        self.assertEqual(len(result.summaries), 1)
        self.assertEqual(result.excluded_papers, [])
        self.assertFalse(any(w.startswith(("Excluded paper '", "No papers passed")) for w in result.warnings))

    def test_empty_supplied_papers_never_trigger_search(self):
        search = FixtureSearch([RuntimeError("Search must not run")])
        result = IntegratedResearchWorkflow(search).run("Controlled topic", papers=[])
        self.assertEqual(search.calls, [])
        self.assertEqual(result.summaries, [])

    def test_summary_with_wrong_source_or_invented_quote_is_not_accepted(self):
        for mutation in ("url", "quote"):
            with self.subTest(mutation=mutation):
                summarizer = FixtureSummarizer()
                summary = summarizer.summarize(paper("a"))
                if mutation == "url":
                    summary.source_url = "https://example.org/other"
                else:
                    summary.evidence_quotes["dataset"] = "Invented quotation"
                workflow = IntegratedResearchWorkflow(summarizer=SimpleNamespace(summarize=lambda p: summary))
                result = workflow.run("Controlled topic", 1, papers=[paper("a")], include_thematic_review=False)
                self.assertEqual(result.summaries, [])
                self.assertTrue(result.stage_errors)

    def test_unquoted_claims_remain_not_reported(self):
        summarizer = FixtureSummarizer()
        summary = summarizer.summarize(paper("a"))
        summary.dataset = "Invented dataset"
        workflow = IntegratedResearchWorkflow(summarizer=SimpleNamespace(summarize=lambda p: summary))
        result = workflow.run("Controlled topic", 1, papers=[paper("a")], include_thematic_review=False)
        self.assertEqual(result.summaries[0].dataset, NOT_REPORTED)

    def test_legacy_result_defaults_and_unknown_fields_remain_strict(self):
        raw = encode(ResearchWorkflowResult("Legacy topic"))
        for name in ("requested_papers", "summary_sources", "stage_errors", "search_complete"):
            raw["fields"].pop(name)
        loaded = decode(raw)
        self.assertIsNone(loaded.requested_papers)
        self.assertEqual(loaded.stage_errors, {})
        raw["fields"]["unexpected"] = True
        with self.assertRaises(ValueError):
            decode(raw)

    def test_in_memory_legacy_result_with_missing_factory_fields_can_be_captured(self):
        old = ResearchWorkflowResult("Legacy topic")
        del old.summary_sources
        del old.stage_errors
        loaded = decode(encode(old))
        self.assertEqual(loaded.stage_errors, {})

    def test_saved_job_resumes_after_interruption_without_repeating_summary_or_mastery(self):
        with tempfile.TemporaryDirectory(prefix="phss_research_job_") as temp:
            store = SQLiteStudentStore(Path(temp) / "students.sqlite3")
            owner = store.create_profile("Alice")
            state = student_state(owner)
            search = FixtureSearch([[paper("a"), paper("b")]])
            summarizer = FixtureSummarizer()
            workflow = IntegratedResearchWorkflow(search, summarizer)
            coordinator = PersonalizedResearchCoordinator(state["student"], state["orchestrator"].cognitive_engine, workflow)
            state["advanced_research_job"] = dict(request=dict(topic="Controlled topic", concept_name="Classification",
                       limit=2, include_thematic_review=False), outcome=None, complete=False)
            revision, interrupted = 0, False
            def save():
                nonlocal revision, interrupted
                revision = store.save(owner, capture(state), revision)
                result = state.get("advanced_research_result")
                if result and len(result.summaries) == 1 and not interrupted:
                    interrupted = True
                    raise RuntimeError("Controlled interruption after durable summary")
            with self.assertRaisesRegex(RuntimeError, "Controlled interruption"):
                run_analysis_job(state, coordinator, save)
            _, payload = store.load(owner)
            state = restore(payload, owner, OfflineOrchestrator)
            coordinator = PersonalizedResearchCoordinator(state["student"], state["orchestrator"].cognitive_engine, workflow)
            run_analysis_job(state, coordinator, save)
            self.assertEqual(summarizer.calls, ["a", "b"])
            self.assertEqual(len(search.calls), 1)
            self.assertTrue(state["advanced_research_job"]["complete"])
            self.assertEqual(state["student"].get_concept("Classification").attempts, 0)
            self.assertEqual(state["orchestrator"].cognitive_engine.evidence_store.get_all_evidence(), [])


if __name__ == "__main__":
    unittest.main()
