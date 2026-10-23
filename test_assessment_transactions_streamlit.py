"""Offline Streamlit failure -> refresh -> explicit Resume integration."""
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from app.persistence.sqlite_store import SQLiteStudentStore
from test_persistence_streamlit import OfflineOrchestrator


class FailingFollowup:
    def __init__(self):
        self.failed = False

    def create_content(self, request):
        if request.cognitive_context["attempts"] > 0 and not self.failed:
            self.failed = True
            raise RuntimeError("Synthetic follow-up outage")
        return "Synthetic offline lesson"


class AssessmentResumeUITests(unittest.TestCase):
    def test_refresh_then_resume_preserves_one_answer_and_one_cognitive_update(self):
        with tempfile.TemporaryDirectory(prefix="phss_resume_ui_") as temp:
            store = SQLiteStudentStore(Path(temp) / "students.sqlite3")
            owner = store.create_profile("Alice")
            provider = FailingFollowup()
            evaluations = []
            def factory(cognitive_engine=None):
                orchestrator = OfflineOrchestrator(cognitive_engine)
                orchestrator.learning_runtime.content_provider = provider
                original = orchestrator.learning_runtime.answer_evaluator.evaluate
                def evaluate(answer):
                    evaluations.append(answer)
                    return original(answer)
                orchestrator.learning_runtime.answer_evaluator.evaluate = evaluate
                return orchestrator
            original_connect = socket.socket.connect
            def local_connect(sock, address):
                if address[0] not in ("127.0.0.1", "::1"):
                    self.fail("Unexpected external API call")
                return original_connect(sock, address)
            entry = str(Path(__file__).parent / "review_ui.py")
            with patch("app.persistence.streamlit_state.SQLiteStudentStore", lambda path: store), \
                 patch("app.orchestrator.orchestrator_runtime.OrchestratorRuntime", factory), \
                 patch("socket.socket.connect", local_connect):
                app = AppTest.from_file(entry, default_timeout=15)
                app.query_params["student"] = owner
                app.run()
                app.text_input(key="learning_request_input").set_value("Teach recursion")
                next(b for b in app.button if b.label == "Start").click().run()
                app.selectbox(key="selected_practice_question_count").select(5)
                next(b for b in app.button if b.label == "Start Adaptive Practice").click().run()
                next(t for t in app.text_area if t.label == "Your answer").set_value("answer")
                next(b for b in app.button if b.label == "Submit Answer").click().run()
                self.assertTrue(app.error)
                self.assertEqual(app.session_state.student.get_concept("Recursion").attempts, 1)
                self.assertEqual(app.session_state.practice_session.questions_completed, 1)
                refreshed = AppTest.from_file(entry, default_timeout=15)
                refreshed.query_params["student"] = owner
                refreshed.run()
                self.assertFalse(refreshed.exception)
                next(b for b in refreshed.button if b.label == "Resume saved assessment").click().run()
                self.assertFalse(refreshed.exception, refreshed.exception)
                self.assertFalse(refreshed.error, [e.value for e in refreshed.error])
                self.assertNotIn("_assessment_pending", refreshed.session_state)
                self.assertEqual(len(evaluations), 1)
                self.assertEqual(refreshed.session_state.student.get_concept("Recursion").attempts, 1)
                self.assertEqual(refreshed.session_state.practice_session.questions_completed, 1)
                self.assertEqual(len(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence()), 1)
                next(b for b in refreshed.button if b.label.startswith("Next Question")).click().run()
                self.assertFalse(refreshed.exception)
                self.assertTrue(any(t.label == "Your answer" for t in refreshed.text_area))


if __name__ == "__main__":
    unittest.main()
