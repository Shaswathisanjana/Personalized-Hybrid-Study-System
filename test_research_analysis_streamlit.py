"""Offline main-app research retrieval, recovery and genuine diagnostic journeys."""
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.session_recovery import capture
from app.research_agent.personalized_coordinator import PersonalizedResearchCoordinator
from app.research_agent.research_workflow import IntegratedResearchWorkflow
from app.cognitive.evidence import LearningEvidence
from test_research_analysis_recovery import FixtureSearch, FixtureSummarizer, paper
from test_student_persistence import student_state
from test_persistence_streamlit import OfflineOrchestrator, OfflineQuiz, OfflineEvaluator


class ResearchAnalysisUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phss_research_ui_")
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteStudentStore(Path(self.temp.name) / "students.sqlite3")
        self.owner = self.store.create_profile("Alice")
        self.bob = self.store.create_profile("Bob")
        self.search = FixtureSearch([[paper("a"), paper("b"), paper("rejected", "")]])
        self.summarizer = FixtureSummarizer(["b"])
        def factory(student, cognitive_engine):
            return PersonalizedResearchCoordinator(student, cognitive_engine,
                IntegratedResearchWorkflow(self.search, self.summarizer))
        original_connect = socket.socket.connect
        def local_connect(sock, address):
            if address[0] not in ("127.0.0.1", "::1"):
                raise AssertionError("Unexpected external network call")
            return original_connect(sock, address)
        for target, replacement in (
            ("app.persistence.streamlit_state.SQLiteStudentStore", lambda path: self.store),
            ("app.orchestrator.orchestrator_runtime.OrchestratorRuntime", OfflineOrchestrator),
            ("app.research_agent.streamlit_page.PersonalizedResearchCoordinator", factory),
            ("app.cognitive.diagnostic_intervention.GeminiQuizGenerator", OfflineQuiz),
            ("app.cognitive.diagnostic_intervention.AnswerEvaluator", OfflineEvaluator),
            ("socket.socket.connect", local_connect),
        ):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self):
        app = AppTest.from_file(str(Path(__file__).parent / "review_ui.py"), default_timeout=20)
        app.query_params["student"] = self.owner
        app.run()
        app.radio[0].set_value("Advanced Research Agent").run()
        self.healthy(app)
        return app

    def healthy(self, app):
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertFalse(app.error, [e.value for e in app.error])

    @staticmethod
    def button(app, label):
        return next(b for b in app.button if b.label == label)

    def generate(self, app):
        next(t for t in app.text_input if t.label == "Research topic").set_value("Controlled topic")
        next(t for t in app.text_input if t.label == "Learning concept to personalize").set_value("Classification")
        next(s for s in app.slider if s.label == "Number of papers").set_value(3)
        self.button(app, "Generate Research Analysis").click().run()
        self.healthy(app)

    def seed_conflicts(self, topics):
        state = student_state(self.owner)
        engine = state["orchestrator"].cognitive_engine
        for topic in topics:
            for source, performance in (("learning", .95), ("coding", .05)):
                engine.process_evidence(state["student"], LearningEvidence(
                    self.owner, topic, source, "controlled_test_observation", performance, .6, .9))
            self.assertTrue(engine.has_conflict(self.owner, topic))
        self.store.save(self.owner, capture(state), 0)

    def test_partial_analysis_refresh_and_retry_preserves_sources_and_no_mastery(self):
        app = self.app()
        self.generate(app)
        self.assertEqual(len(app.session_state.advanced_research_result.summaries), 1)
        self.assertEqual(len(app.session_state.advanced_research_result.excluded_papers), 1)
        self.assertTrue(app.session_state.advanced_research_result.stage_errors)
        calls = len(self.search.calls)
        self.assertEqual(calls, 2)
        refreshed = self.app()
        self.assertEqual(self.summarizer.calls, ["a", "b"])
        self.summarizer.failures.clear()
        self.button(refreshed, "Retry unfinished research analysis").click().run()
        self.healthy(refreshed)
        self.assertEqual(self.summarizer.calls, ["a", "b", "b"])
        self.assertEqual(len(self.search.calls), calls)
        self.assertEqual(len(refreshed.session_state.advanced_research_result.summaries), 2)
        self.assertTrue(refreshed.session_state.advanced_research_job["complete"])
        self.assertEqual(refreshed.session_state.student.get_concept("Classification").attempts, 0)
        self.assertEqual(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])
        self.assertTrue(any("2/3" in w for w in refreshed.session_state.advanced_research_result.warnings))

    def test_failed_search_refresh_retries_saved_request(self):
        self.search.batches = [RuntimeError("Controlled retrieval failure")]
        app = self.app()
        self.generate(app)
        self.assertIn("search", app.session_state.advanced_research_result.stage_errors)
        self.search.batches = [[paper("a")]]
        self.summarizer.failures.clear()
        refreshed = self.app()
        self.button(refreshed, "Retry unfinished research analysis").click().run()
        self.healthy(refreshed)
        self.assertEqual(len(refreshed.session_state.advanced_research_result.summaries), 1)
        self.assertTrue(refreshed.session_state.advanced_research_job["complete"])

    def test_profile_switch_keeps_analysis_jobs_separate(self):
        app = self.app()
        self.generate(app)
        app.selectbox(key="_profile_selector").select(self.bob).run()
        self.healthy(app)
        self.assertNotIn("advanced_research_job", app.session_state)
        self.assertIsNone(app.session_state.advanced_research_result)
        app.selectbox(key="_profile_selector").select(self.owner).run()
        self.healthy(app)
        self.assertEqual(len(app.session_state.advanced_research_result.summaries), 1)

    def test_genuine_diagnostic_is_available_without_generating_research(self):
        self.seed_conflicts(["Classification"])
        app = self.app()
        self.button(app, "Generate CACM Diagnostic Question").click().run()
        self.healthy(app)
        refreshed = self.app()
        next(t for t in refreshed.text_area if t.label == "Your diagnostic answer").set_value("answer")
        self.button(refreshed, "Submit Diagnostic Answer").click().run()
        self.healthy(refreshed)
        self.assertTrue(any("Diagnostic assessment completed" in s.value for s in refreshed.success))
        self.assertEqual(len(self.search.calls), 0)
        self.assertEqual(len(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence()), 3)

    def test_multiple_conflicts_keep_active_diagnostic_topic_after_refresh(self):
        self.seed_conflicts(["Classification", "Strings"])
        app = self.app()
        app.selectbox(key="research_other_conflict").select("Strings").run()
        self.button(app, "Generate CACM Diagnostic Question").click().run()
        self.healthy(app)
        session_id = app.session_state.research_diagnostic_session.session_id
        refreshed = self.app()
        self.assertEqual(refreshed.session_state.research_diagnostic_session.session_id, session_id)
        self.assertEqual(refreshed.session_state.research_diagnostic_session.concept_name, "Strings")
        self.assertTrue(refreshed.selectbox(key="research_other_conflict").disabled)


if __name__ == "__main__":
    unittest.main()
