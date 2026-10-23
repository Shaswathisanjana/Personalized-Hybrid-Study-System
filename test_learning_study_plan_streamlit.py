"""Temporary SQLite and offline providers exercise the actual Streamlit page."""
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from app.cognitive.evidence import LearningEvidence
from app.persistence.session_recovery import capture
from app.persistence.sqlite_store import SQLiteStudentStore
from test_student_persistence import student_state
from test_persistence_streamlit import OfflineOrchestrator
from test_learning_study_planner import OfflineResources


class StudyPlanUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phss_plan_ui_")
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteStudentStore(Path(self.temp.name) / "students.sqlite3")
        self.owner = self.store.create_profile("Alice")
        self.bob = self.store.create_profile("Bob")
        self.evaluations = []
        self.fail_evaluation = False
        def factory(cognitive_engine=None):
            orchestrator = OfflineOrchestrator(cognitive_engine)
            orchestrator.learning_runtime.resource_recommender = OfflineResources()
            evaluate = orchestrator.learning_runtime.answer_evaluator.evaluate
            def counting_evaluator(answer):
                self.evaluations.append(answer)
                if self.fail_evaluation:
                    raise RuntimeError("Controlled diagnostic provider outage")
                return evaluate(answer)
            orchestrator.learning_runtime.answer_evaluator.evaluate = counting_evaluator
            return orchestrator
        self.factory = factory
        original_connect = socket.socket.connect
        def local_connect(sock, address):
            if address[0] not in ("127.0.0.1", "::1"):
                raise AssertionError("Unexpected external network call")
            return original_connect(sock, address)
        for target, replacement in (
            ("app.persistence.streamlit_state.SQLiteStudentStore", lambda path: self.store),
            ("app.orchestrator.orchestrator_runtime.OrchestratorRuntime", factory),
            ("socket.socket.connect", local_connect),
        ):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self, owner=None):
        app = AppTest.from_file(str(Path(__file__).parent / "review_ui.py"), default_timeout=20)
        app.query_params["student"] = owner or self.owner
        app.run()
        self.healthy(app)
        return app

    def healthy(self, app):
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertFalse(app.error, [e.value for e in app.error])

    @staticmethod
    def button(app, label):
        return next(button for button in app.button if button.label == label)

    def save_goal(self, app, topic="Python Recursion"):
        app.selectbox(key="learning_plan_goal_choice").select(topic)
        self.button(app, "Save study goal").click().run()
        self.healthy(app)

    def seed_conflict(self):
        state = student_state(self.owner)
        engine, student = state["orchestrator"].cognitive_engine, state["student"]
        for source, score in (("learning", .95), ("coding", .05)):
            engine.process_evidence(student, LearningEvidence(self.owner, "Python Recursion", source,
                                    "controlled_test_observation", score, .6, .9))
        self.assertTrue(engine.has_conflict(self.owner, "recursion"))
        state["learning_goal"] = "Python Recursion"
        self.store.save(self.owner, capture(state), 0)

    def test_goal_refresh_switch_and_restart_preserve_student_isolation(self):
        app = self.app()
        self.save_goal(app)
        self.assertEqual(app.session_state.student.concepts, {})
        refreshed = self.app()
        self.assertEqual(refreshed.session_state.learning_goal, "Python Recursion")
        self.button(refreshed, "Restart Current Activity").click().run()
        self.healthy(refreshed)
        self.assertEqual(refreshed.session_state.learning_goal, "Python Recursion")
        refreshed.selectbox(key="_profile_selector").select(self.bob).run()
        self.healthy(refreshed)
        self.assertNotIn("learning_goal", refreshed.session_state)
        refreshed.selectbox(key="_profile_selector").select(self.owner).run()
        self.healthy(refreshed)
        self.assertEqual(refreshed.session_state.learning_goal, "Python Recursion")

    def test_custom_goal_persists_without_claiming_prerequisite_knowledge(self):
        app = self.app()
        app.selectbox(key="learning_plan_goal_choice").select("Custom topic")
        app.text_input(key="learning_plan_custom_goal").set_value("Compiler Design")
        self.button(app, "Save study goal").click().run()
        self.healthy(app)
        self.assertEqual(self.app().session_state.learning_goal, "Compiler Design")
        self.assertEqual(app.session_state.student.concepts, {})

    def test_prerequisite_opens_without_evidence_and_active_practice_is_protected(self):
        app = self.app()
        self.save_goal(app)
        self.button(app, "Open recommended learning activity").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.last_result.route.concept, "Python Basics")
        self.assertEqual(app.session_state.student.get_concept("Python Basics").attempts, 0)
        self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])
        self.button(app, "Start Adaptive Practice").click().run()
        self.healthy(app)
        self.assertTrue(self.button(app, "Open recommended learning activity").disabled)
        refreshed = self.app()
        self.assertEqual(refreshed.session_state.practice_session.session_id, app.session_state.practice_session.session_id)
        self.assertTrue(self.button(refreshed, "Open recommended learning activity").disabled)

    def test_real_conflict_diagnostic_survives_refresh_and_submits_once(self):
        self.seed_conflict()
        app = self.app()
        self.button(app, "Generate learning diagnostic").click().run()
        self.healthy(app)
        session_id = app.session_state.learning_diagnostic_session.session_id
        refreshed = self.app()
        self.assertEqual(refreshed.session_state.learning_diagnostic_session.session_id, session_id)
        next(t for t in refreshed.text_area if t.label == "Your diagnostic answer").set_value("answer")
        self.button(refreshed, "Submit learning diagnostic").click().run()
        self.healthy(refreshed)
        self.assertEqual(len(self.evaluations), 1)
        self.assertIsNone(refreshed.session_state.learning_diagnostic_session)
        final = self.app()
        self.assertIsNotNone(final.session_state.learning_diagnostic_outcome)
        engine = final.session_state.orchestrator.cognitive_engine
        self.assertEqual(len(engine.evidence_store.get_all_evidence()), 3)
        self.assertEqual(len(self.evaluations), 1)

    def test_diagnostic_failure_refresh_and_explicit_resume(self):
        self.seed_conflict()
        app = self.app()
        self.button(app, "Generate learning diagnostic").click().run()
        next(t for t in app.text_area if t.label == "Your diagnostic answer").set_value("answer")
        self.fail_evaluation = True
        self.button(app, "Submit learning diagnostic").click().run()
        self.assertTrue(app.error)
        refreshed = self.app()
        self.assertEqual(refreshed.session_state["_assessment_pending"]["kind"], "learning_diagnostic")
        self.fail_evaluation = False
        self.button(refreshed, "Resume saved assessment").click().run()
        self.healthy(refreshed)
        self.assertNotIn("_assessment_pending", refreshed.session_state)
        self.assertEqual(len(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence()), 3)

    def test_resource_formats_and_three_plus_view_more_are_preserved(self):
        from app.learning_agent.resources.models import LearningResource, RankedLearningResource, ResourceRecommendation
        from app.learning_agent.runtime import LearningExperience
        from app.orchestrator.orchestrator_runtime import OrchestratorResult, AgentExecutionResult
        from app.orchestrator.query_router import QueryRoute
        state = student_state(self.owner)
        # These reserved example.org URLs are controlled UI fixtures, never production retrieval.
        resources = [RankedLearningResource(LearningResource(
            f"Controlled resource {index}", f"https://example.org/fixture/{index}", kind,
            source="Offline UI fixture"), 1, 1, 1, 1, "Fixture ranking")
            for index, kind in enumerate(("video", "article", "documentation", "video", "documentation"))]
        service = self.factory(state["orchestrator"].cognitive_engine).learning_runtime
        experience = LearningExperience(service.get_next_activity(state["student"], "Python Basics"),
                                        ResourceRecommendation("Python Basics", "easy", resources))
        route = QueryRoute("Fixture", "Python Basics", ["learn"], ["learning"], True, "Offline UI fixture")
        state["last_result"] = OrchestratorResult("Fixture", route, [AgentExecutionResult("learning", True, experience)])
        self.store.save(self.owner, capture(state), 0)
        app = self.app()
        self.assertTrue(any("Showing 3 of 5 resources" in caption.value for caption in app.caption))
        self.button(app, "View More Resources (2 more)").click().run()
        self.healthy(app)
        self.assertTrue(any("Showing 5 of 5 resources" in caption.value for caption in app.caption))
        app.selectbox(key="learning_resource_format_Python Basics").select("Documentation").run()
        self.healthy(app)
        self.assertTrue(any("Showing 2 of 2 resources" in caption.value for caption in app.caption))
        self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])


if __name__ == "__main__":
    unittest.main()
