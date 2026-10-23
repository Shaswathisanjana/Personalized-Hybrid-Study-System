"""Actual main-page coding selection, assessment, hints and refresh with offline providers."""
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from app.persistence.sqlite_store import SQLiteStudentStore
from app.persistence.session_recovery import capture
from app.coding_agent.verified_exercises import get_verified_exercise
from app.coding_agent.code_runner import ControlledCodeRunner
from test_student_persistence import student_state
from test_persistence_streamlit import OfflineOrchestrator
import test_verified_coding_catalog as catalog_tests
from test_verified_coding_catalog import SOLUTIONS


class CodingPracticeUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phss_coding_ui_")
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteStudentStore(Path(self.temp.name) / "students.sqlite3")
        self.alice = self.store.create_profile("Alice")
        self.bob = self.store.create_profile("Bob")
        self.evaluations = []
        def evaluator_factory():
            evaluator = catalog_tests.EvaluationGuardrailTests().evaluator()
            evaluator.code_runner = ControlledCodeRunner()
            original = evaluator.evaluate
            def evaluate(submission, test_cases):
                self.evaluations.append(submission)
                return original(submission, test_cases)
            evaluator.evaluate = evaluate
            return evaluator
        original_connect = socket.socket.connect
        def local_connect(sock, address):
            if address[0] not in ("127.0.0.1", "::1"):
                raise AssertionError("Unexpected external call")
            return original_connect(sock, address)
        for target, replacement in (
            ("app.persistence.streamlit_state.SQLiteStudentStore", lambda path: self.store),
            ("app.orchestrator.orchestrator_runtime.OrchestratorRuntime", OfflineOrchestrator),
            ("app.coding_agent.integrated_workflow.CodingEvaluator", evaluator_factory),
            ("socket.socket.connect", local_connect),
        ):
            patcher = patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)

    def app(self):
        app = AppTest.from_file(str(Path(__file__).parent / "review_ui.py"), default_timeout=20)
        app.query_params["student"] = self.alice
        app.run()
        app.radio[0].set_value("Advanced Coding Agent").run()
        self.healthy(app)
        return app

    def healthy(self, app):
        self.assertFalse(app.exception, [e.message for e in app.exception])
        self.assertFalse(app.error, [e.value for e in app.error])

    def seed(self, concept, mastery, confidence=.8, attempts=4, legacy=False):
        state = student_state(self.alice)
        concept_state = state["student"].get_concept(concept)
        concept_state.mastery, concept_state.confidence, concept_state.attempts = mastery, confidence, attempts
        if legacy:
            exercise = get_verified_exercise("Recursion")
            exercise.task.difficulty = "hard"  # Earlier versions merely relabelled factorial.
            state.update(advanced_coding_exercise=exercise, advanced_coding_loaded_concept="Recursion",
                         advanced_coding_concept="Recursion", advanced_coding_editor="# Saved original work")
        self.store.save(self.alice, capture(state), 0)

    def test_recommended_levels_load_distinct_tasks(self):
        app = self.app()
        app.button(key="advanced_coding_load").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.advanced_coding_exercise.task.difficulty, "easy")
        self.assertEqual(app.session_state.student.get_concept("Recursion").attempts, 0)
        app.selectbox(key="advanced_coding_concept").select("Strings").run()
        app.button(key="advanced_coding_load").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.advanced_coding_exercise.task.title, "Count Vowels")
        self.assertEqual(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_hard_submission_refresh_and_duplicate_use_one_actual_assessment(self):
        self.seed("Strings", .9)
        app = self.app()
        app.selectbox(key="advanced_coding_concept").select("Strings").run()
        app.button(key="advanced_coding_load").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.advanced_coding_exercise.task.title, "Longest Substring Without Repeats")
        app.text_area(key="advanced_coding_editor").set_value(SOLUTIONS[("Strings", "hard")])
        app.button(key="advanced_coding_submit").click().run()
        self.healthy(app)
        self.assertEqual(len(self.evaluations), 1)
        self.assertEqual(self.evaluations[0].task.difficulty, "hard")
        evidence = app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence()
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].source_agent, "coding")
        self.assertEqual(app.session_state.student.get_concept("Strings").attempts, 5)
        refreshed = self.app()
        self.assertEqual(refreshed.session_state.advanced_coding_exercise.task.difficulty, "hard")
        self.assertEqual(refreshed.session_state.advanced_coding_editor, SOLUTIONS[("Strings", "hard")])
        refreshed.button(key="advanced_coding_submit").click().run()
        self.healthy(refreshed)
        self.assertEqual(len(self.evaluations), 1)
        self.assertEqual(refreshed.session_state.student.get_concept("Strings").attempts, 5)
        refreshed.selectbox(key="_profile_selector").select(self.bob).run()
        self.healthy(refreshed)
        self.assertNotIn("advanced_coding_exercise", refreshed.session_state)

    def test_medium_selection_and_task_specific_hints_survive_refresh(self):
        self.seed("Recursion", .6)
        app = self.app()
        app.button(key="advanced_coding_load").click().run()
        self.healthy(app)
        self.assertEqual(app.session_state.advanced_coding_exercise.task.title, "Sum a Nested List Recursively")
        for _ in range(2):
            app.button(key="advanced_coding_next_hint").click().run()
            self.healthy(app)
        self.assertEqual(len(app.session_state.advanced_coding_hint_history), 2)
        self.assertTrue(any("sublist" in hint.message for hint in app.session_state.advanced_coding_hint_history))
        refreshed = self.app()
        self.assertEqual(len(refreshed.session_state.advanced_coding_hint_history), 2)
        refreshed.button(key="advanced_coding_next_hint").click().run()
        self.healthy(refreshed)
        self.assertEqual([h.level for h in refreshed.session_state.advanced_coding_hint_history], [1, 2, 3])
        self.assertTrue(refreshed.button(key="advanced_coding_next_hint").disabled)
        self.assertEqual(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_legacy_saved_exercise_is_explained_and_not_overwritten(self):
        self.seed("Recursion", .9, legacy=True)
        app = self.app()
        self.assertTrue(any("earlier specification" in info.value for info in app.info))
        self.assertEqual(app.session_state.advanced_coding_exercise.task.title, "Factorial Using Recursion")
        self.assertEqual(app.session_state.advanced_coding_editor, "# Saved original work")

    def test_new_concepts_expose_genuine_conflict_in_diagnostic_tab(self):
        from app.cognitive.evidence import LearningEvidence
        state = student_state(self.alice)
        engine = state["orchestrator"].cognitive_engine
        for source, score in (("learning", .95), ("coding", .05)):
            engine.process_evidence(state["student"], LearningEvidence(
                self.alice, "Strings", source, "controlled_test_observation", score, .6, .9))
        self.assertTrue(engine.has_conflict(self.alice, "Strings"))
        self.store.save(self.alice, capture(state), 0)
        app = self.app()
        selector = next(s for s in app.selectbox if s.label == "Select a conflicted concept")
        self.assertIn("Strings", selector.options)


if __name__ == "__main__":
    unittest.main()
