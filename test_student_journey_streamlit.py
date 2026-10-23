"""Actual main-app handoffs between preserved learning/coding/research pages."""
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest
from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.session_recovery import capture
from app.orchestrator.orchestrator_runtime import OrchestratorRuntime
from app.orchestrator.query_router import QueryRoute
from app.cognitive.evidence import LearningEvidence
from test_persistence_streamlit import OfflineOrchestrator
from test_learning_study_planner import OfflineResources
from test_student_persistence import student_state
from test_student_journey import RecursionQuiz, RecursionEvaluator


class RoutedOfflineOrchestrator(OfflineOrchestrator):
    def __init__(self, cognitive_engine=None):
        super().__init__(cognitive_engine)
        self.learning_runtime.resource_recommender = OfflineResources()
        self.query_router = SimpleNamespace(route=self.route)

    @staticmethod
    def route(query):
        agents = ["coding", "research"] if "code and research" in query.lower() else ["learning"]
        return QueryRoute(query, "Recursion", [], agents, True, "Controlled offline routing")

    _run_learning = OrchestratorRuntime._run_learning


class StudentJourneyUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phss_journey_ui_")
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteStudentStore(Path(self.temp.name) / "students.sqlite3")
        self.alice, self.bob = self.store.create_profile("Alice"), self.store.create_profile("Bob")
        original_connect = socket.socket.connect
        def local_connect(sock, address):
            if address[0] not in ("127.0.0.1", "::1"):
                raise AssertionError("Unexpected external network call")
            return original_connect(sock, address)
        for target, replacement in (
            ("app.persistence.streamlit_state.SQLiteStudentStore", lambda path: self.store),
            ("app.orchestrator.orchestrator_runtime.OrchestratorRuntime", RoutedOfflineOrchestrator),
            ("app.cognitive.diagnostic_intervention.GeminiQuizGenerator", RecursionQuiz),
            ("app.cognitive.diagnostic_intervention.AnswerEvaluator", RecursionEvaluator),
            ("socket.socket.connect", local_connect),
        ):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self):
        app = AppTest.from_file(str(Path(__file__).parent / "review_ui.py"), default_timeout=20)
        app.query_params["student"] = self.alice
        app.run()
        self.healthy(app)
        return app

    def healthy(self, app):
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertFalse(app.error, [e.value for e in app.error])

    @staticmethod
    def button(app, label):
        return next(button for button in app.button if button.label == label)

    def start(self, app, query):
        app.text_input(key="learning_request_input").set_value(query)
        self.button(app, "Start").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.journey_topic, "Recursion")

    def test_natural_request_opens_verified_practice_then_prefilled_research_and_keeps_draft(self):
        app = self.app()
        self.start(app, "Give me code and research on recursion")
        self.assertEqual(len(app.session_state.last_result.agent_results), 2)
        self.button(app, "Open coding practice").click().run()
        self.healthy(app)
        self.assertEqual(app.radio[0].value, "Advanced Coding Agent")
        self.assertEqual(app.selectbox(key="advanced_coding_concept").value, "Recursion")
        app.button(key="advanced_coding_load").click().run()
        self.healthy(app)
        app.text_area(key="advanced_coding_editor").set_value("# Saved student draft").run()
        self.button(app, "Continue research").click().run()
        self.healthy(app)
        self.assertEqual(app.radio[0].value, "Advanced Research Agent")
        self.assertEqual(app.text_input(key="advanced_research_concept_input").value, "Recursion")
        self.assertIsNone(app.session_state.advanced_research_result)
        refreshed = self.app()
        self.assertEqual(refreshed.radio[0].value, "Advanced Research Agent")
        self.button(refreshed, "Continue coding practice").click().run()
        self.healthy(refreshed)
        self.assertEqual(refreshed.text_area(key="advanced_coding_editor").value, "# Saved student draft")
        self.assertEqual(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_unfinished_learning_quiz_survives_workflow_switch_and_return(self):
        app = self.app()
        self.start(app, "Teach recursion")
        self.button(app, "Start Adaptive Practice").click().run()
        self.healthy(app)
        session_id = app.session_state.practice_session.session_id
        question_id = app.session_state.practice_session.current_question.question_id
        self.button(app, "Continue research").click().run()
        self.healthy(app)
        self.button(app, "Continue learning").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.practice_session.session_id, session_id)
        self.assertEqual(app.session_state.practice_session.current_question.question_id, question_id)
        self.assertEqual(app.session_state.practice_session.questions_completed, 0)
        self.assertTrue(any(t.label == "Your answer" for t in app.text_area))

    def test_custom_topic_disables_unsupported_coding_without_blocking_research(self):
        app = self.app()
        app.text_input(key="journey_topic_draft").set_value("Quantum Computing")
        self.button(app, "Use this study topic").click().run()
        self.healthy(app)
        self.assertTrue(self.button(app, "Continue coding practice").disabled)
        self.button(app, "Continue research").click().run()
        self.healthy(app)
        self.assertEqual(app.text_input(key="advanced_research_topic_input").value, "Quantum Computing")

    def test_profile_switch_keeps_handoffs_and_context_separate(self):
        app = self.app()
        app.text_input(key="journey_topic_draft").set_value("Recursion")
        self.button(app, "Use this study topic").click().run()
        self.button(app, "Continue research").click().run()
        self.healthy(app)
        app.selectbox(key="_profile_selector").select(self.bob).run()
        self.healthy(app)
        self.assertNotIn("journey_topic", app.session_state)
        self.assertNotIn("journey_navigation", app.session_state)
        self.assertEqual(app.text_input(key="advanced_research_topic_input").value, "")
        self.assertEqual(app.text_input(key="journey_topic_draft").value, "")
        app.selectbox(key="_profile_selector").select(self.alice).run()
        self.healthy(app)
        self.assertEqual(app.session_state.journey_topic, "Recursion")
        self.assertEqual(app.text_input(key="advanced_research_concept_input").value, "Recursion")

    def test_conflict_handoff_uses_existing_concept_alias_and_real_diagnostic(self):
        state = student_state(self.alice)
        engine = state["orchestrator"].cognitive_engine
        for source, score in (("learning", .95), ("coding", .05)):
            engine.process_evidence(state["student"], LearningEvidence(
                self.alice, "Recursion", source, "controlled_test_observation", score, .7, .9))
        state["journey_topic"] = "Python Recursion"
        self.store.save(self.alice, capture(state), 0)
        app = self.app()
        self.button(app, "Resolve conflicting evidence").click().run()
        self.healthy(app)
        self.assertEqual(app.selectbox(key="research_other_conflict").value, "Recursion")
        self.button(app, "Generate CACM Diagnostic Question").click().run()
        self.healthy(app)
        next(t for t in app.text_area if t.label == "Your diagnostic answer").set_value("A base case")
        self.button(app, "Submit Diagnostic Answer").click().run()
        self.healthy(app)
        self.assertFalse(app.session_state.orchestrator.cognitive_engine.has_conflict(self.alice, "recursion"))
        self.assertFalse(any(b.label == "Resolve conflicting evidence" for b in app.button))
        self.assertEqual(len(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence()), 3)


if __name__ == "__main__":
    unittest.main()
