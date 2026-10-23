"""Offline identity and cross-agent evidence tests; scenarios are synthetic."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from app.cognitive.concept_identity import concept_id
from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.diagnostic_intervention import DiagnosticIntervention
from app.learning_agent.agent import LearningAgent
from app.learning_agent.runtime import LearningAgentRuntime
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult
from app.learning_agent.progress_tracker import LearningProgressTracker
from app.learning_agent.topic_bank import LearningTopicBank
from app.coding_agent.agent import CodingAgent
from app.coding_agent.agentic_review_coordinator import AgenticCodeReviewCoordinator
from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.models import CodingSubmission, CodingEvaluation
from app.coding_agent.verified_exercises import get_verified_exercise
from app.research_agent.agent import ResearchAgent
from app.research_agent.cacm_runtime import ResearchCACMRuntime
from app.research_agent.models import ResearchComprehensionQuestion, ResearchComprehensionEvaluation


class ConceptIdentityTests(unittest.TestCase):
    def test_explicit_aliases_case_and_spacing(self):
        aliases = ["Recursion", "recursion", "Python Recursion", "  PYTHON   RECURSION  ", "Recursion in Python"]
        self.assertEqual({concept_id(name) for name in aliases}, {"recursion"})
        student = StudentCognitiveModel("alice")
        first = student.get_concept(aliases[0])
        for name in aliases:
            self.assertIs(student.get_concept(name), first)
        self.assertEqual(len(student.concepts), 1)
        self.assertEqual(first.attempts, 0)
        self.assertEqual(first.concept_name, "Recursion")

    def test_custom_topics_and_distinct_topics_are_preserved(self):
        student = StudentCognitiveModel("alice")
        first = student.get_concept("My Custom Topic")
        self.assertIs(student.get_concept(" MY   CUSTOM topic "), first)
        for left, right in [("Python Lists", "Arrays"), ("SQL Recursion", "Recursion"),
                            ("Recursive Neural Networks", "Recursion"), ("C", "C++"),
                            ("Java Loops", "Python Loops"), ("Factorial", "Recursion")]:
            self.assertNotEqual(concept_id(left), concept_id(right))
            self.assertIsNot(student.get_concept(left), student.get_concept(right))
        self.assertIsNone(student.find_concept("Unseen Topic"))
        self.assertNotIn("Unseen Topic", student.concepts)
        with self.assertRaises(ValueError):
            concept_id(" ")

    def test_progress_and_topic_browser_share_identity_without_changing_labels(self):
        student = StudentCognitiveModel("alice")
        tracker = LearningProgressTracker()
        first = tracker.start_topic("alice", "Python Recursion")
        self.assertIs(tracker.start_topic("alice", "recursion"), first)
        student.get_concept("RECURSION").mastery = .73
        self.assertEqual(tracker.snapshot(student, "Recursion").mastery, .73)
        tracker.complete_practice_session("alice", "recursion", 5, "session-1")
        tracker.complete_practice_session("alice", "Python Recursion", 5, "session-1")
        self.assertEqual(first.completed_practice_sessions, 1)
        bank = LearningTopicBank()
        self.assertEqual(len(bank.all_topics()), 50)
        self.assertEqual(bank.get("Recursion").name, "Python Recursion")
        self.assertEqual(bank.get("python recursion"), bank.get("Recursion"))
        self.assertEqual(bank.prerequisites_for("Recursion")[0].name, "Python Functions")

    def test_verified_coding_lookup_does_not_guess_broad_synonyms(self):
        self.assertEqual(get_verified_exercise("Python Recursion").task.concept_name, "Recursion")
        self.assertEqual(AgenticCodeReviewCoordinator.normalize_concept("Python Recursion"), "Recursion")
        for name in ("Python Lists", "Factorial", "Recursive Neural Networks", "SQL Recursion"):
            self.assertEqual(AgenticCodeReviewCoordinator.normalize_concept(name), "")

    def test_real_agent_bridges_share_alias_evidence_and_resolve_conflicts(self):
        student = StudentCognitiveModel("alice")
        engine = CognitiveEngine()
        learning = LearningAgentRuntime(engine,
            quiz_generator=Mock(),
            answer_evaluator=SimpleNamespace(evaluate=lambda answer: EvaluationResult(True, 1.0, "Synthetic correct answer")),
            misconception_analyzer=Mock(), resource_recommender=object())
        question = QuizQuestion("Python Recursion", "easy", "Synthetic question", correct_answer="answer")
        learning.submit_practice_answer(student, question, "answer")
        state = student.get_concept("Recursion")
        self.assertEqual(state.attempts, 1)
        exercise = get_verified_exercise("recursion")
        coding = IntegratedCodingWorkflow(student, engine, evaluator=SimpleNamespace(
            evaluate=lambda **kwargs: CodingEvaluation(False, 0.0, .9, "Synthetic incorrect code")))
        coding.submit_student_code(CodingSubmission("alice", exercise.task, "synthetic input"), exercise.test_cases)
        self.assertTrue(engine.has_conflict("alice", "PYTHON RECURSION"))
        research = ResearchCACMRuntime(engine, student)
        research.process_comprehension("alice",
            ResearchComprehensionQuestion("recursion in python", "Synthetic research question", "A", "E"),
            ResearchComprehensionEvaluation(False, 0.0, .9, "Synthetic incorrect answer"))
        self.assertEqual(state.attempts, 3)
        self.assertEqual(len(student.concepts), 1)
        self.assertEqual(len(engine.evidence_store.get_evidence_for_concept("alice", "recursion")), 3)
        self.assertTrue(engine.get_conflicts("alice", "Recursion"))
        self.assertEqual(CodingAgent().choose_action(student, "Recursion", True).action_type, "diagnostic_coding")
        self.assertEqual(ResearchAgent().choose_action(student, "Python Recursion", True).action_type, "diagnostic_research")
        intervention = DiagnosticIntervention(engine,
            quiz_generator=SimpleNamespace(generate=lambda **kwargs: QuizQuestion("RECursion", "medium", "Diagnostic", correct_answer="A")),
            answer_evaluator=SimpleNamespace(evaluate=lambda answer: EvaluationResult(True, 1.0, "Synthetic diagnostic answer")))
        session = intervention.start(student, "recursion in python")
        outcome = intervention.submit_answer(student, session, "A")
        self.assertFalse(outcome.has_active_conflict)
        self.assertTrue(outcome.conflict_resolved)
        self.assertEqual(state.attempts, 4)
        self.assertNotEqual(LearningAgent().choose_action(student, "Recursion", engine.has_conflict("alice", "Recursion")).action_type, "diagnostic_quiz")
        self.assertEqual(engine.evidence_store.get_all_evidence()[0].concept_name, "Python Recursion")
        self.assertFalse(engine.has_conflict("bob", "Recursion"))


if __name__ == "__main__":
    unittest.main()
