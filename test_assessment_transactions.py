"""Synthetic, offline fault-injection tests for assessed evidence and recovery."""
from copy import deepcopy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.runtime import LearningAgentRuntime
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult
from app.learning_agent.practice_session import PracticeSession
from app.coding_agent.models import CodingEvaluation, CodingSubmission
from app.coding_agent.verified_exercises import get_verified_exercise
from app.coding_agent.submission_controller import CodingSubmissionController
from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.research_agent.models import ResearchComprehensionQuestion, ResearchComprehensionEvaluation
from app.research_agent.personalized_coordinator import PersonalizedResearchCoordinator
from app.research_agent.assessment_service import ResearchAssessmentService
from app.research_agent.research_workflow import ResearchWorkflowResult
from app.cognitive.diagnostic_intervention import DiagnosticIntervention, DiagnosticSession
from app.cognitive.cross_agent_runtime import CrossAgentRuntime
from app.research_agent.diagnostic_bridge import ResearchDiagnosticBridge
from app.persistence.sqlite_store import SQLiteStudentStore, StaleSnapshotError
from app.persistence.streamlit_state import load_profile, save_state
from app.persistence.assessment_recovery import resume_assessment
from app.persistence.state_codec import encode, decode
from app.persistence.session_recovery import capture


class QuizGenerator:
    def __init__(self):
        self.fail = False
        self.calls = 0

    def generate(self, concept_name, difficulty, **kwargs):
        self.calls += 1
        if self.fail:
            self.fail = False
            raise RuntimeError("next question unavailable")
        return QuizQuestion(concept_name, difficulty, "Synthetic question", correct_answer="answer")


class ContentProvider:
    def __init__(self):
        self.fail = False

    def create_content(self, request):
        if self.fail:
            self.fail = False
            raise RuntimeError("content unavailable")
        return "Synthetic lesson"


class AssessmentTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="phss_transaction_")
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteStudentStore(Path(self.temp.name) / "students.sqlite3")
        self.store.create_profile("Alice", student_id="alice")
        self.evaluator = Mock()
        self.evaluator.evaluate.side_effect = lambda answer: EvaluationResult(True, 1.0, "Synthetic evaluation")
        self.generator = QuizGenerator()
        self.provider = ContentProvider()

    def factory(self, engine):
        runtime = LearningAgentRuntime(engine, content_provider=self.provider,
            quiz_generator=self.generator, answer_evaluator=self.evaluator,
            misconception_analyzer=Mock(), resource_recommender=object())
        return SimpleNamespace(cognitive_engine=engine, learning_runtime=runtime)

    def state(self):
        result = {}
        load_profile(result, self.store, "alice", self.factory)
        return result

    def learning(self, count=3):
        state = self.state()
        start = state["orchestrator"].learning_runtime.start_practice_session(
            state["student"], "Recursion", max_questions=count)
        state["practice_session"] = start.session
        state["_assessment_pending"] = {"kind": "learning", "request": {
            "answer": "answer", "question_id": start.question.question_id}}
        save_state(state)
        return state

    def submit(self, state):
        return state["orchestrator"].learning_runtime.submit_practice_session_answer(
            state["student"], state["practice_session"], "answer",
            question_id=state["_assessment_pending"]["request"]["question_id"])

    def fail_after_cognitive_commit(self, engine, stage):
        original = engine.persist_state
        hit = []
        def callback():
            if not hit and any(stage in record["stages"] for record in engine.assessment_records.values()):
                hit.append(True)
                raise RuntimeError("failure after committed evidence")
            original()
        engine.persist_state = callback

    def test_evidence_replay_and_changed_payload_rejected(self):
        student, engine = StudentCognitiveModel("alice"), CognitiveEngine()
        evidence = LearningEvidence("alice", "Recursion", "learning", "quiz", .9, .6, .8)
        engine.process_evidence(student, evidence)
        engine.process_evidence(student, deepcopy(evidence))
        self.assertEqual(student.get_concept("Recursion").attempts, 1)
        self.assertEqual(len(engine.evidence_store.get_all_evidence()), 1)
        changed = deepcopy(evidence)
        changed.performance = .1
        with self.assertRaisesRegex(ValueError, "reused"):
            engine.process_evidence(student, changed)
        self.assertEqual(student.get_concept("Recursion").attempts, 1)

    def test_cognitive_processing_and_save_failure_roll_back_all_mutations(self):
        for failure in ("processing", "saving"):
            student, engine = StudentCognitiveModel("alice"), CognitiveEngine()
            concept = student.get_concept("Recursion")
            before = deepcopy(concept)
            if failure == "processing":
                engine.misconception_manager.record_support = Mock(side_effect=RuntimeError("processing failed"))
            else:
                engine.persist_state = Mock(side_effect=RuntimeError("saving failed"))
            evidence = LearningEvidence("alice", "Recursion", "coding", "quiz", .1, .6, .8, ["Synthetic misconception"])
            with self.assertRaises(RuntimeError):
                engine.process_evidence(student, evidence)
            self.assertIs(student.get_concept("Recursion"), concept)
            self.assertEqual(concept, before)
            self.assertEqual(engine.evidence_store.get_all_evidence(), [])
            self.assertEqual(engine.evidence_receipts, {})
            self.assertEqual(engine.active_conflicts, {})

    def test_followup_content_failure_resumes_without_evaluating_again(self):
        state = self.learning()
        self.provider.fail = True
        with self.assertRaisesRegex(RuntimeError, "content unavailable"):
            self.submit(state)
        self.assertEqual(state["student"].get_concept("Recursion").attempts, 1)
        self.assertEqual(state["practice_session"].questions_completed, 1)
        recovered = self.state()
        self.evaluator.evaluate.side_effect = AssertionError("must not evaluate twice")
        resume_assessment(recovered)
        save_state(recovered)
        self.assertEqual(self.evaluator.evaluate.call_count, 1)
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 1)
        self.assertEqual(recovered["practice_session"].questions_completed, 1)
        self.assertIsNotNone(recovered["practice_session"].current_question)
        self.assertNotIn("_assessment_pending", recovered)

    def test_next_question_failure_resumes_with_saved_history(self):
        state = self.learning()
        self.generator.fail = True
        with self.assertRaisesRegex(RuntimeError, "next question unavailable"):
            self.submit(state)
        recovered = self.state()
        resume_assessment(recovered)
        self.assertEqual(self.evaluator.evaluate.call_count, 1)
        self.assertEqual(recovered["practice_session"].questions_completed, 1)
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 1)

    def test_final_answer_recovery_records_completion_once(self):
        state = self.learning(count=1)
        request = deepcopy(state["_assessment_pending"])
        self.provider.fail = True
        with self.assertRaises(RuntimeError):
            self.submit(state)
        recovered = self.state()
        resume_assessment(recovered)
        recovered["_assessment_pending"] = request
        resume_assessment(recovered)
        progress = recovered["learning_progress_tracker"].get_progress("alice", "Recursion")
        self.assertEqual(progress.completed_practice_sessions, 1)
        self.assertEqual(progress.total_practice_questions, 1)
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 1)
        self.assertEqual(self.evaluator.evaluate.call_count, 1)

    def test_changed_answer_is_rejected_after_failure(self):
        state = self.learning()
        self.provider.fail = True
        with self.assertRaises(RuntimeError):
            self.submit(state)
        with self.assertRaisesRegex(ValueError, "different answer"):
            state["orchestrator"].learning_runtime.submit_practice_session_answer(
                state["student"], state["practice_session"], "changed answer",
                question_id=state["_assessment_pending"]["request"]["question_id"])
        self.assertEqual(self.evaluator.evaluate.call_count, 1)

    def test_provider_failure_before_evaluation_retries_only_unfinished_work(self):
        state = self.learning()
        self.evaluator.evaluate.side_effect = [RuntimeError("provider unavailable"), EvaluationResult(True, 1.0, "Synthetic")]
        with self.assertRaises(RuntimeError):
            self.submit(state)
        self.assertEqual(state["student"].get_concept("Recursion").attempts, 0)
        recovered = self.state()
        resume_assessment(recovered)
        self.assertEqual(self.evaluator.evaluate.call_count, 2)
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 1)

    def test_stale_tab_is_rejected_before_evaluation(self):
        first = self.learning()
        stale = self.state()
        self.submit(first)
        calls = self.evaluator.evaluate.call_count
        with self.assertRaises(StaleSnapshotError):
            self.submit(stale)
        self.assertEqual(self.evaluator.evaluate.call_count, calls)
        self.assertEqual(self.state()["student"].get_concept("Recursion").attempts, 1)

    def test_coding_recovery_after_commit_does_not_evaluate_or_score_again(self):
        state = self.state()
        engine = state["orchestrator"].cognitive_engine
        evaluator = Mock()
        evaluator.evaluate.return_value = CodingEvaluation(True, 1.0, .9, "Synthetic")
        exercise = get_verified_exercise("Recursion")
        controller = CodingSubmissionController(IntegratedCodingWorkflow(state["student"], engine, evaluator=evaluator), exercise)
        code = "def factorial(n): return 1"
        state.update(advanced_coding_controller=controller, advanced_coding_exercise=exercise,
                     _assessment_pending={"kind": "coding", "request": {"code": code}})
        self.fail_after_cognitive_commit(engine, "cognitive_outcome")
        with self.assertRaises(RuntimeError):
            controller.submit(code)
        recovered = self.state()
        recovered["advanced_coding_controller"].workflow.evaluator = Mock(side_effect=AssertionError("must not evaluate"))
        resume_assessment(recovered)
        self.assertEqual(evaluator.evaluate.call_count, 1)
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 1)
        self.assertEqual(len(recovered["orchestrator"].cognitive_engine.evidence_store.get_all_evidence()), 1)

    def test_research_recovery_after_commit_uses_saved_evaluation(self):
        state = self.state()
        engine = state["orchestrator"].cognitive_engine
        evaluator = Mock()
        evaluator.evaluate.return_value = ResearchComprehensionEvaluation(True, .9, .8, "Synthetic")
        service = ResearchAssessmentService(PersonalizedResearchCoordinator(state["student"], engine), evaluator=evaluator)
        question = ResearchComprehensionQuestion("Recursion", "Synthetic Q", "A", "E")
        state.update(advanced_research_result=ResearchWorkflowResult("Recursion"), research_assessment_service=service,
            _assessment_pending={"kind": "research", "request": {"question": question, "answer": "A"}})
        self.fail_after_cognitive_commit(engine, "cognitive_outcome")
        with self.assertRaises(RuntimeError):
            service.submit_answer("alice", question, "A")
        recovered = self.state()
        resume_assessment(recovered)
        self.assertTrue(recovered["research_assessment_completed"])
        self.assertEqual(evaluator.evaluate.call_count, 1)
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 1)

    def test_diagnostic_recovery_after_conflict_resolution_does_not_reassess(self):
        state = self.state()
        student, engine = state["student"], state["orchestrator"].cognitive_engine
        for source, score in (("learning", .95), ("coding", .1)):
            engine.process_evidence(student, LearningEvidence("alice", "Recursion", source, "quiz", score, .6, .8))
        evaluator = Mock()
        evaluator.evaluate.return_value = EvaluationResult(True, 1.0, "Synthetic diagnostic")
        intervention = DiagnosticIntervention(engine, quiz_generator=Mock(), answer_evaluator=evaluator)
        bridge = ResearchDiagnosticBridge(student, engine, CrossAgentRuntime(engine, intervention))
        session = DiagnosticSession("alice", "Recursion", QuizQuestion("Recursion", "medium", "Q"), "medium")
        state.update(research_diagnostic_bridge=bridge, research_diagnostic_session=session,
            _assessment_pending={"kind": "research_diagnostic", "request": {"session": session, "answer": "A"}})
        self.fail_after_cognitive_commit(engine, "cognitive_result")
        with self.assertRaises(RuntimeError):
            bridge.submit_answer(session, "A")
        recovered = self.state()
        self.assertFalse(recovered["orchestrator"].cognitive_engine.has_conflict("alice", "Recursion"))
        resume_assessment(recovered)
        self.assertEqual(evaluator.evaluate.call_count, 1)
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 3)
        self.assertTrue(recovered["research_diagnostic_outcome"].diagnostic_outcome.conflict_resolved)

    def test_legacy_model_ids_are_stable_and_old_fields_remain_required(self):
        for value, names in ((QuizQuestion("Recursion", "easy", "Q"), ["question_id"]),
            (PracticeSession("alice", "Recursion"), ["session_id", "pending_assessment_id"]),
            (LearningEvidence("alice", "Recursion", "learning", "quiz", 1., .6, .8), ["evidence_id"])):
            old = encode(value)
            for name in names:
                old["fields"].pop(name)
            first, second = decode(old), decode(old)
            stable_name = next(n for n in names if n != "pending_assessment_id")
            self.assertEqual(getattr(first, stable_name), getattr(second, stable_name))
            old["fields"].pop("concept_name")
            with self.assertRaises(ValueError):
                decode(old)

    def test_identical_prompts_are_separate_questions_and_old_ids_do_not_recount(self):
        state = self.learning()
        first_id = state["practice_session"].current_question.question_id
        self.submit(state)
        second_id = state["practice_session"].current_question.question_id
        self.assertNotEqual(first_id, second_id)
        runtime = state["orchestrator"].learning_runtime
        runtime.submit_practice_session_answer(state["student"], state["practice_session"], "answer", question_id=second_id)
        runtime.submit_practice_session_answer(state["student"], state["practice_session"], "answer", question_id=first_id)
        self.assertEqual(self.evaluator.evaluate.call_count, 2)
        self.assertEqual(state["student"].get_concept("Recursion").attempts, 2)

    def test_guided_review_failure_does_not_repeat_coding_evaluation(self):
        state = self.state()
        engine = state["orchestrator"].cognitive_engine
        evaluator, reviewer = Mock(), Mock()
        evaluator.evaluate.return_value = CodingEvaluation(True, 1.0, .9, "Synthetic")
        reviewer.review_submission.side_effect = [RuntimeError("review unavailable"), "Synthetic review"]
        exercise = get_verified_exercise("Recursion")
        workflow = IntegratedCodingWorkflow(state["student"], engine, evaluator=evaluator, guided_reviewer=reviewer)
        submission = CodingSubmission("alice", exercise.task, "synthetic original code")
        with self.assertRaisesRegex(RuntimeError, "review unavailable"):
            workflow.submit_student_code(submission, exercise.test_cases, include_guided_review=True)
        result = workflow.submit_student_code(submission, exercise.test_cases, include_guided_review=True)
        self.assertEqual(evaluator.evaluate.call_count, 1)
        self.assertEqual(reviewer.review_submission.call_count, 2)
        self.assertEqual(state["student"].get_concept("Recursion").attempts, 1)
        self.assertEqual(result.guided_review, "Synthetic review")

    def test_old_snapshot_backup_and_historical_replay_are_safe(self):
        state = self.state()
        concept = state["student"].get_concept("Recursion")
        concept.attempts, concept.mastery = 2, .72  # Synthetic pre-migration state.
        old_evidence = LearningEvidence("alice", "Recursion", "learning", "quiz", .9, .6, .8)
        state["orchestrator"].cognitive_engine.evidence_store.evidence_history.append(old_evidence)
        state["practice_session"] = PracticeSession("alice", "Recursion")
        state["practice_session"].set_current_question(QuizQuestion("Recursion", "easy", "Old question"))
        payload = capture(state)
        payload.pop("assessment_transaction_version")
        data = decode(payload["data"])
        data.pop("assessment_records")
        data.pop("evidence_receipts")
        payload["data"] = encode(data)
        additions = {
            "app.cognitive.evidence.LearningEvidence": ("evidence_id",),
            "app.learning_agent.quiz_models.QuizQuestion": ("question_id",),
            "app.learning_agent.practice_session.PracticeSession": ("session_id", "pending_assessment_id"),
        }
        def remove_new_fields(value):
            if isinstance(value, dict):
                for name in additions.get(value.get("type"), ()):
                    value["fields"].pop(name, None)
                for nested in value.values():
                    remove_new_fields(nested)
            elif isinstance(value, list):
                for nested in value:
                    remove_new_fields(nested)
        remove_new_fields(payload)
        self.store.save("alice", payload, 0)
        recovered = self.state()
        engine = recovered["orchestrator"].cognitive_engine
        historical = engine.evidence_store.get_all_evidence()[0]
        result = engine.process_evidence(recovered["student"], deepcopy(historical))
        self.assertTrue(result["replayed"])
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 2)
        self.assertEqual(recovered["student"].get_concept("Recursion").mastery, .72)
        save_state(recovered)
        self.assertEqual(self.store.transaction_backups("alice"), [(1, payload)])
        again = self.state()
        self.assertEqual(again["practice_session"].current_question.question_id,
                         recovered["practice_session"].current_question.question_id)

    def test_receipts_survive_a_fresh_runtime(self):
        state = self.learning()
        self.submit(state)
        evidence = state["orchestrator"].cognitive_engine.evidence_store.get_all_evidence()[0]
        recovered = self.state()
        recovered["orchestrator"].cognitive_engine.process_evidence(recovered["student"], deepcopy(evidence))
        self.assertEqual(recovered["student"].get_concept("Recursion").attempts, 1)
        self.assertEqual(len(recovered["orchestrator"].cognitive_engine.evidence_store.get_all_evidence()), 1)


if __name__ == "__main__":
    unittest.main()
