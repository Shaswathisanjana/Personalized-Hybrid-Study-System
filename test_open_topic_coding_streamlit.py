"""Real main-page widgets, profile snapshots and subprocess evaluation, offline."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import test_coding_practice_streamlit as curated_ui
from test_open_topic_coding import package
from app.coding_agent.open_topic import OpenTopicGenerator
from app.coding_agent.guided_review_coordinator import GuidedCodeReviewCoordinator
from app.coding_agent.ai_code_reviewer import AIReviewResult


class OpenTopicUITests(unittest.TestCase):
    setUp = curated_ui.CodingPracticeUITests.setUp
    app = curated_ui.CodingPracticeUITests.app
    def healthy(self, app):
        self.assertFalse(app.exception, [e.message for e in app.exception])
        # This suite deliberately submits incorrect code. The expected failed
        # behavioral cases are feedback widgets, not an application failure.
        unexpected = [e.value for e in app.error if not e.value.startswith("FAIL: ")]
        self.assertFalse(unexpected, unexpected)

    def generator(self, fail=False):
        self.requests = []
        def provider(**request):
            self.requests.append(request)
            if fail:
                raise ValueError("unavailable offline provider")
            return package(request["difficulty"])
        patcher = patch("app.coding_agent.streamlit_page.OpenTopicGenerator",
                        side_effect=lambda **kw: OpenTopicGenerator(provider=provider, **kw))
        patcher.start()
        self.addCleanup(patcher.stop)

    def load(self, app):
        app.text_input(key="advanced_coding_free_topic").set_value(" Merge Sort ").run()
        app.button(key="advanced_coding_load").click().run(timeout=90)
        self.healthy(app)

    def test_generated_hints_refresh_original_assessment_and_verified_review(self):
        self.generator()
        app = self.app()
        before = len(app.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence())
        self.load(app)
        exercise = app.session_state.advanced_coding_exercise
        self.assertEqual(exercise.task.concept_name, "merge sort")
        self.assertIsNone(app.session_state.student.find_concept("merge sort"))
        self.assertEqual(len(self.requests), 1)
        app.button(key="advanced_coding_next_hint").click().run()
        self.healthy(app)
        self.assertEqual(len(app.session_state.advanced_coding_hint_history), 1)
        app.text_area(key="advanced_coding_editor").set_value("# draft before navigation").run()
        app.radio[0].set_value("Student View").run()
        app.radio[0].set_value("Advanced Coding Agent").run()
        self.healthy(app)
        self.assertEqual(app.session_state.advanced_coding_free_topic, " Merge Sort ")
        self.assertEqual(app.session_state.advanced_coding_editor, "# draft before navigation")
        refreshed = self.app()
        self.assertEqual(refreshed.session_state.advanced_coding_free_topic, " Merge Sort ")
        self.assertEqual(refreshed.session_state.advanced_coding_exercise.package_id, exercise.package_id)
        self.assertEqual(len(refreshed.session_state.advanced_coding_hint_history), 1)
        self.assertEqual(len(self.requests), 1)
        original_code = "def merge_lists(a, b):\n    return []\n"
        refreshed.text_area(key="advanced_coding_editor").set_value(original_code)
        refreshed.button(key="advanced_coding_submit").click().run()
        self.healthy(refreshed)
        self.assertEqual(len(self.evaluations), 1)
        self.assertEqual(self.evaluations[0].code, original_code)
        self.assertFalse(refreshed.session_state.advanced_coding_submission_record.result.evaluation.is_correct)
        self.assertAlmostEqual(refreshed.session_state.advanced_coding_submission_record.result.evaluation.performance, 1/3)
        self.assertEqual([e.value for e in refreshed.error], ["FAIL: interleaved", "FAIL: duplicates"])
        self.assertEqual(refreshed.session_state.student.find_concept("merge sort").attempts, 1)
        self.assertEqual(len(refreshed.session_state.orchestrator.cognitive_engine.evidence_store.get_all_evidence()), before+1)
        reviewer = SimpleNamespace(review=lambda **kw: AIReviewResult("Offline correction", corrected_code=exercise.reference_code))
        with patch("app.coding_agent.streamlit_page.GuidedCodeReviewCoordinator",
                   side_effect=lambda: GuidedCodeReviewCoordinator(reviewer=reviewer)):
            refreshed.button(key="advanced_coding_guided_review").click().run()
        self.healthy(refreshed)
        self.assertEqual(refreshed.session_state.advanced_coding_guided_result.correction_status, "passed_supplied_tests")
        again = self.app()
        self.healthy(again)
        again.button(key="advanced_coding_submit").click().run()
        self.healthy(again)
        self.assertEqual(len(self.evaluations), 1)
        self.assertEqual(again.session_state.student.find_concept("merge sort").attempts, 1)
        again.selectbox(key="_profile_selector").select(self.bob).run()
        self.healthy(again)
        self.assertNotIn("advanced_coding_exercise", again.session_state)
        self.assertFalse(again.session_state.advanced_coding_free_topic)
        self.assertIsNone(again.session_state.student.find_concept("merge sort"))

    def test_failed_generation_preserves_previous_exercise_and_draft(self):
        self.generator(fail=True)
        app = self.app()
        app.button(key="advanced_coding_load").click().run()
        app.text_area(key="advanced_coding_editor").set_value("# keep my draft").run()
        previous = app.session_state.advanced_coding_exercise
        self.load(app)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(app.session_state.advanced_coding_exercise, previous)
        self.assertEqual(app.session_state.advanced_coding_editor, "# keep my draft")
        self.assertIsNone(app.session_state.student.find_concept("merge sort"))
        refreshed = self.app()
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(refreshed.session_state.advanced_coding_editor, "# keep my draft")
        refreshed.text_input(key="advanced_coding_free_topic").set_value("").run()
        self.healthy(refreshed)
        self.assertEqual(refreshed.session_state.advanced_coding_exercise, previous)

    def test_unsupported_language_transparent_and_no_generation(self):
        self.generator()
        app = self.app()
        app.text_input(key="advanced_coding_free_topic").set_value("SQL joins").run()
        app.selectbox(key="advanced_coding_language").select("SQL").run()
        self.healthy(app)
        self.assertTrue(any("not supported" in w.value for w in app.warning))
        self.assertEqual(self.requests, [])
        self.assertFalse(any(b.key == "advanced_coding_submit" for b in app.button))

    def test_custom_topic_genuine_conflict_remains_visible(self):
        from app.cognitive.evidence import LearningEvidence
        from app.persistence.session_recovery import capture
        from test_student_persistence import student_state
        state = student_state(self.alice)
        engine = state["orchestrator"].cognitive_engine
        for source, score in (("learning", .95), ("coding", .05)):
            engine.process_evidence(state["student"], LearningEvidence(
                self.alice, "merge sort", source, "controlled_test_observation", score, .6, .9))
        self.assertTrue(engine.has_conflict(self.alice, "merge sort"))
        self.store.save(self.alice, capture(state), 0)
        app = self.app()
        app.text_input(key="advanced_coding_free_topic").set_value("merge sort").run()
        self.healthy(app)
        self.assertTrue(any("diagnostic_coding" in info.value for info in app.info))
        selector = next(s for s in app.selectbox if s.label == "Select a conflicted concept")
        self.assertIn("merge sort", selector.options)


if __name__ == "__main__":
    unittest.main()
