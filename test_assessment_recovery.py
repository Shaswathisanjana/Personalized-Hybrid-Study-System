"""Offline recovery checks: no provider calls or execution of student code."""
import hashlib
import json
import os
from dataclasses import asdict
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("GEMINI_API_KEY", "offline-test-placeholder")

from app.learning_agent.practice_session import PracticeSession
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult
from app.persistence.session_recovery import capture, restore
from app.research_agent.assessment_service import ResearchAssessmentService
from app.research_agent.models import ResearchComprehensionQuestion
from app.research_agent.research_workflow import ResearchWorkflowResult
from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.submission_controller import CodingSubmissionController, CodingSubmissionRecord
from app.coding_agent.verified_exercises import get_verified_exercise
from app.cognitive.diagnostic_intervention import DiagnosticSession
from app.cognitive.cross_agent_runtime import CrossAgentRuntime
from app.cognitive.diagnostic_intervention import DiagnosticIntervention
from app.coding_agent.diagnostic_bridge import CodingDiagnosticBridge
from test_student_persistence import student_state, offline_orchestrator


class AssessmentRecoveryTests(unittest.TestCase):
    def test_active_practice_roundtrip(self):
        state = student_state("alice")
        session = PracticeSession("alice", "Recursion", max_questions=10)
        q1 = QuizQuestion("Recursion", "easy", "Q1", correct_answer="A1")
        session.set_current_question(q1)
        session.record_attempt("A1", EvaluationResult(True, 1.0, "Correct"))
        q2 = QuizQuestion("Recursion", "medium", "Q2", correct_answer="A2")
        session.set_current_question(q2)
        session._progress_completion_id = "stable-completion"
        state.update(practice_session=session, practice_concept="Recursion",
                     waiting_for_next_question=True, last_student_answer="A1")
        recovered = restore(capture(state), "alice", offline_orchestrator)
        current = recovered["practice_session"]
        self.assertEqual(current.max_questions, 10)
        self.assertEqual(current.current_question, q2)
        self.assertEqual(current.questions_completed, 1)
        self.assertEqual(current._progress_completion_id, "stable-completion")
        self.assertEqual(current.attempts[0].student_answer, "A1")
        self.assertEqual(recovered["student"].concepts, {})

    def test_coding_duplicate_guard_survives_recovery(self):
        state = student_state("alice")
        exercise = get_verified_exercise("Recursion")
        workflow = IntegratedCodingWorkflow(state["student"], state["orchestrator"].cognitive_engine)
        controller = CodingSubmissionController(workflow, exercise)
        code = "def factorial(n): return 1"
        identity = controller._submission_id(code)
        # Synthetic completed result; this test measures guard restoration only.
        controller.records[identity] = CodingSubmissionRecord(identity, None)
        state.update(advanced_coding_exercise=exercise, advanced_coding_controller=controller)
        recovered = restore(capture(state), "alice", offline_orchestrator)
        restored = recovered["advanced_coding_controller"]
        self.assertIs(restored.workflow.student, recovered["student"])
        self.assertIs(restored.workflow.cognitive_engine, recovered["orchestrator"].cognitive_engine)
        with patch.object(restored.workflow, "submit_student_code", side_effect=AssertionError("must not reassess")):
            record, is_new = restored.submit(code)
        self.assertFalse(is_new)
        self.assertEqual(record.submission_id, identity)
        self.assertEqual(recovered["student"].concepts, {})

    def test_research_duplicate_guard_survives_recovery(self):
        from app.research_agent.personalized_coordinator import PersonalizedResearchCoordinator
        state = student_state("alice")
        coordinator = PersonalizedResearchCoordinator(state["student"], state["orchestrator"].cognitive_engine)
        service = ResearchAssessmentService(coordinator)
        question = ResearchComprehensionQuestion("Recursion", "Why?", "Answer", "Explanation")
        fingerprint = hashlib.sha256(json.dumps(asdict(question), sort_keys=True).encode()).hexdigest()
        service._submitted_question_ids.add(fingerprint)
        state.update(advanced_research_result=ResearchWorkflowResult("Recursion"),
                     research_assessment_question=question, research_assessment_service=service,
                     research_assessment_completed=True)
        recovered = restore(capture(state), "alice", offline_orchestrator)
        restored = recovered["research_assessment_service"]
        restored.evaluator = Mock(side_effect=AssertionError("must not reassess"))
        with self.assertRaisesRegex(ValueError, "already been submitted"):
            restored.submit_answer("alice", recovered["research_assessment_question"], "Answer")
        restored.evaluator.assert_not_called()
        self.assertIs(restored.coordinator.student, recovered["student"])

    def test_pending_submission_is_preserved_without_replaying(self):
        state = student_state("alice")
        state["_assessment_pending"] = "learning"
        recovered = restore(capture(state), "alice", offline_orchestrator)
        self.assertEqual(recovered["_assessment_pending"], "learning")
        self.assertEqual(recovered["orchestrator"].cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_diagnostic_session_and_guard_roundtrip(self):
        state = student_state("alice")
        engine = state["orchestrator"].cognitive_engine
        intervention = DiagnosticIntervention(engine, quiz_generator=Mock(), answer_evaluator=Mock())
        runtime = CrossAgentRuntime(engine, intervention)
        bridge = CodingDiagnosticBridge(state["student"], engine, cross_agent_runtime=runtime)
        session = DiagnosticSession("alice", "Recursion", QuizQuestion("Recursion", "medium", "Q"), "medium")
        intervention.completed_sessions[session.session_id] = None
        state.update(advanced_coding_diagnostic_session=session, advanced_coding_diagnostic_bridge=bridge)
        recovered = restore(capture(state), "alice", offline_orchestrator)
        restored = recovered["advanced_coding_diagnostic_bridge"]
        self.assertIn(session.session_id, restored.runtime.diagnostic_intervention.completed_sessions)
        self.assertEqual(recovered["advanced_coding_diagnostic_session"].session_id, session.session_id)
        self.assertIs(restored.student, recovered["student"])
        self.assertIs(restored.cognitive_engine, recovered["orchestrator"].cognitive_engine)


if __name__ == "__main__":
    unittest.main()
