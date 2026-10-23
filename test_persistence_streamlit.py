"""Main-app recovery with Streamlit AppTest and offline backend construction."""
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.session_recovery import capture
from test_student_persistence import student_state
from app.learning_agent.runtime import LearningAgentRuntime, LearningExperience
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult
from app.orchestrator.orchestrator_runtime import OrchestratorResult, AgentExecutionResult
from app.orchestrator.query_router import QueryRoute


class OfflineQuiz:
    def generate(self, concept_name, difficulty, **kwargs):
        number = len(kwargs.get("previous_questions") or []) + 1
        return QuizQuestion(concept_name, difficulty, f"Offline question {number}",
                            correct_answer="answer", explanation="Controlled test question")


class OfflineEvaluator:
    def evaluate(self, student_answer):
        correct = student_answer.answer == "answer"
        return EvaluationResult(correct, 1.0 if correct else 0.0, "Controlled feedback")


class OfflineMisconceptions:
    def analyze(self, student_answer):
        return []


class OfflineOrchestrator:
    def __init__(self, cognitive_engine=None):
        self.cognitive_engine = cognitive_engine
        self.learning_runtime = LearningAgentRuntime(
            cognitive_engine, quiz_generator=OfflineQuiz(), answer_evaluator=OfflineEvaluator(),
            misconception_analyzer=OfflineMisconceptions(), resource_recommender=object())

    def handle_query(self, student, query):
        route = QueryRoute(query, "Recursion", ["learn"], ["learning"], True, "Offline test route")
        activity = self.learning_runtime.get_next_activity(student, "Recursion")
        return OrchestratorResult(query, route, [AgentExecutionResult(
            "learning", True, LearningExperience(activity))])


class PersistenceStreamlitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phss_ui_test_")
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteStudentStore(Path(self.temp.name) / "students.sqlite3")
        self.alice = self.store.create_profile("Alice")
        self.bob = self.store.create_profile("Bob")
        state = student_state(self.alice)
        state["student"].get_concept("Recursion").mastery = .72
        state["student"].get_concept("Recursion").attempts = 4
        state["learning_progress_tracker"].complete_practice_session(self.alice, "Recursion", 5, "quiz-1")
        self.store.save(self.alice, capture(state), 0)
        self.entry = str(Path(__file__).parent / "review_ui.py")
        original_connect = socket.socket.connect
        def local_connect(sock, address):
            # Streamlit's Windows event loop uses a loopback socket pair.
            if address[0] not in ("127.0.0.1", "::1"):
                self.fail("Unexpected external network call")
            return original_connect(sock, address)
        for target, replacement in (
            ("app.persistence.streamlit_state.SQLiteStudentStore", lambda path: self.store),
            ("app.orchestrator.orchestrator_runtime.OrchestratorRuntime", OfflineOrchestrator),
            ("socket.socket.connect", local_connect),
        ):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self, profile=None):
        app = AppTest.from_file(self.entry, default_timeout=15)
        if profile:
            app.query_params["student"] = profile
        app.run()
        self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
        self.assertEqual(len(app.error), 0, [e.value for e in app.error])
        return app

    @staticmethod
    def button(app, label):
        return next(b for b in app.button if b.label == label)

    def test_new_browser_session_restores_progress_and_identity(self):
        first = self.app(self.alice)
        second = self.app(self.alice)
        for app in (first, second):
            self.assertEqual(app.session_state.student.user_id, self.alice)
            self.assertEqual(app.session_state.student.get_concept("Recursion").mastery, .72)
            self.assertEqual(app.session_state.student.get_concept("Recursion").attempts, 4)
            self.assertEqual(app.session_state.learning_progress_tracker.get_progress(
                self.alice, "Recursion").completed_practice_sessions, 1)

    def test_switch_profile_and_restart_keep_saved_history(self):
        app = self.app(self.alice)
        app.selectbox(key="_profile_selector").select(self.bob).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state.student.user_id, self.bob)
        self.assertEqual(app.session_state.student.concepts, {})
        app.selectbox(key="_profile_selector").select(self.alice).run()
        self.button(app, "Restart Current Activity").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state.student.get_concept("Recursion").attempts, 4)
        self.assertEqual(app.session_state.learning_progress_tracker.get_progress(
            self.alice, "Recursion").completed_practice_sessions, 1)

    def test_create_profile_selects_new_identity(self):
        app = self.app(self.alice)
        next(t for t in app.text_input if t.label == "New profile name").set_value("Charlie")
        self.button(app, "Create profile").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn(app.session_state.student.user_id, (self.alice, self.bob))
        self.assertEqual(app.session_state.student.concepts, {})
        self.assertEqual(app.query_params["student"], [app.session_state.student.user_id])

    def test_interrupted_submission_is_not_replayed(self):
        revision, _ = self.store.load(self.alice)
        state = student_state(self.alice)
        state["_assessment_pending"] = "learning"
        self.store.save(self.alice, capture(state), revision)
        app = self.app(self.alice)
        self.assertTrue(any("interrupted" in w.value for w in app.warning))
        self.button(app, "Keep progress and discard interrupted activity").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertNotIn("_assessment_pending", app.session_state)
        self.assertEqual(app.session_state.student.concepts, {})

    def test_actual_practice_answer_refresh_and_completion(self):
        app = self.app(self.bob)
        app.text_input(key="learning_request_input").set_value("Teach recursion")
        self.button(app, "Start").click().run()
        self.assertEqual(len(app.exception), 0)
        app.selectbox(key="selected_practice_question_count").select(5)
        self.button(app, "Start Adaptive Practice").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state.practice_session.max_questions, 5)
        # Exercise the existing UI and real learning/CACM pipeline with fake providers.
        for index in range(5):
            editor = next(t for t in app.text_area if "answer" in t.label.lower())
            editor.set_value("answer")
            next(b for b in app.button if b.key == f"submit_practice_{index + 1}").click().run()
            self.assertEqual(len(app.exception), 0, [e.message for e in app.exception])
            self.assertEqual(len(app.error), 0, [e.value for e in app.error])
            self.assertEqual(app.session_state.student.get_concept("Recursion").attempts, index + 1)
            # A new AppTest represents a lost browser session, including lost clients/controllers.
            app = self.app(self.bob)
            self.assertEqual(app.session_state.practice_session.questions_completed, index + 1)
            self.assertEqual(app.session_state.student.get_concept("Recursion").attempts, index + 1)
            if index < 4:
                next(b for b in app.button if b.label.startswith("Next Question")).click().run()
        progress = app.session_state.learning_progress_tracker.get_progress(self.bob, "Recursion")
        self.assertEqual(progress.completed_practice_sessions, 1)
        self.assertEqual(progress.total_practice_questions, 5)
        self.assertEqual(len(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence()), 5)

    def test_stale_browser_tab_cannot_overwrite_newer_progress(self):
        first = self.app(self.alice)
        stale = self.app(self.alice)
        first.text_input(key="learning_request_input").set_value("Newer draft").run()
        saved = self.store.load(self.alice)
        stale.text_input(key="learning_request_input").set_value("Stale draft").run()
        self.assertTrue(any("could not be saved" in e.value for e in stale.error))
        self.assertEqual(self.store.load(self.alice), saved)
        stale.run()
        self.button(stale, "Reload saved profile").click().run()
        self.assertEqual(len(stale.exception), 0)
        self.assertEqual(stale.session_state.learning_request_input, "Newer draft")

    def test_confirmed_clear_affects_only_selected_profile(self):
        app = self.app(self.alice)
        self.assertTrue(self.button(app, "Clear saved progress").disabled)
        next(c for c in app.checkbox if "clears this profile" in c.label).check().run()
        self.button(app, "Clear saved progress").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.session_state.student.user_id, self.alice)
        self.assertEqual(app.session_state.student.concepts, {})
        self.assertEqual(app.session_state.learning_progress_tracker.list_progress(self.alice), [])
        self.assertEqual(self.store.load(self.bob), (0, None))

    def test_existing_memory_session_can_be_imported_explicitly(self):
        app = AppTest.from_file(self.entry, default_timeout=15)
        old_state = student_state("legacy-student")
        old_state["student"].get_concept("Recursion").attempts = 3
        for key, value in old_state.items():
            app.session_state[key] = value
        app.run()
        self.assertEqual(len(app.exception), 0)
        self.button(app, "Import current session into local storage").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0, [e.value for e in app.error])
        self.assertEqual(app.session_state.student.user_id, "legacy-student")
        self.assertEqual(app.session_state.student.get_concept("Recursion").attempts, 3)
        restored = self.app("legacy-student")
        self.assertEqual(restored.session_state.student.get_concept("Recursion").attempts, 3)


if __name__ == "__main__":
    unittest.main()
