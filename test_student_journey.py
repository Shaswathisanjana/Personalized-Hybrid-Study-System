"""Simulated student journey using actual CACM and original-code subprocess tests."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from app.orchestrator.student_journey import StudentJourneyService, request_navigation, apply_navigation
from app.orchestrator.orchestrator_runtime import OrchestratorRuntime
from app.orchestrator.query_router import QueryRoute
from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.learning_agent.runtime import LearningAgentRuntime
from app.learning_agent.practice_session import PracticeSession
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult
from app.learning_agent.diagnostic_bridge import LearningDiagnosticBridge
from app.coding_agent.verified_exercises import get_verified_exercise
from app.coding_agent.submission_controller import CodingSubmissionController
from app.research_agent.models import ResearchPaper, ResearchComprehensionQuestion, ResearchComprehensionEvaluation
from app.research_agent.paper_summarizer import PaperSummary
from app.research_agent.research_workflow import IntegratedResearchWorkflow
from app.research_agent.assessment_service import ResearchAssessmentService
from app.persistence.session_recovery import capture, restore
from test_student_persistence import student_state
from test_persistence_streamlit import OfflineOrchestrator, OfflineMisconceptions
from test_learning_study_planner import OfflineResources
import test_verified_coding_catalog as catalog_tests


class RecursionQuiz:
    def generate(self, concept_name, difficulty, **kwargs):
        return QuizQuestion(concept_name, difficulty, "What stops further calls in a recursive function?",
                            correct_answer="A base case", explanation="A base case stops recursive calls.")


class RecursionEvaluator:
    def evaluate(self, answer):
        correct = answer.answer.strip().casefold() == "a base case"
        return EvaluationResult(correct, 1.0 if correct else 0.0, "Controlled recursion rubric")


def orchestrator():
    instance = OrchestratorRuntime.__new__(OrchestratorRuntime)
    instance.cognitive_engine = CognitiveEngine()
    instance.learning_runtime = LearningAgentRuntime(instance.cognitive_engine, quiz_generator=RecursionQuiz(),
        answer_evaluator=RecursionEvaluator(), misconception_analyzer=OfflineMisconceptions(),
        resource_recommender=OfflineResources())
    return instance


class StudentJourneyTests(unittest.TestCase):
    def test_preview_is_pure_and_unknown_prior_is_unassessed(self):
        student, runtime = StudentCognitiveModel("alice"), orchestrator()
        before = deepcopy(student)
        preview = StudentJourneyService(student, runtime).observe("Python Recursion")
        self.assertEqual(student, before)
        self.assertEqual(preview["attempts"], 0)
        self.assertEqual(preview["coding"].difficulty, "easy")
        self.assertEqual(preview["research"].action_type, "introductory_research")
        self.assertEqual(runtime.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_natural_request_prepares_rich_workflows_without_running_legacy_generators(self):
        student, runtime = StudentCognitiveModel("alice"), orchestrator()
        runtime.query_router = SimpleNamespace(route=lambda query:
            QueryRoute(query, "Recursion", ["code", "research"], ["coding", "research"], True, "Fixture route"))
        result = StudentJourneyService(student, runtime).handle_request("Code and research recursion")
        self.assertEqual([r.agent for r in result.agent_results], ["coding", "research"])
        self.assertTrue(all(r.success and r.output["kind"] == "study_workflow" for r in result.agent_results))
        self.assertEqual(student.concepts, {})
        self.assertEqual(runtime.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_combined_request_executes_learning_and_keeps_both_next_workflows(self):
        student, runtime = StudentCognitiveModel("alice"), orchestrator()
        runtime.query_router = SimpleNamespace(route=lambda query:
            QueryRoute(query, "Recursion", ["learn", "code", "research"], ["learning", "coding", "research"], True, "Fixture route"))
        result = StudentJourneyService(student, runtime).handle_request("Learn, code and research recursion")
        self.assertEqual(len(result.agent_results), 3)
        self.assertTrue(all(r.success for r in result.agent_results))
        self.assertEqual(student.get_concept("recursion").attempts, 0)

    def test_unsupported_coding_topic_is_not_merged_or_relabelled(self):
        service = StudentJourneyService(StudentCognitiveModel("alice"), orchestrator())
        self.assertFalse(service.observe("Python Lists")["coding_available"])
        with self.assertRaises(ValueError):
            service.handoff("coding", "Python Lists")
        with self.assertRaises(ValueError):
            service.handoff("research", "Recursion", diagnostic=True)

    def test_navigation_preserves_existing_work_and_uses_exact_aliases(self):
        state = student_state("alice")
        state["practice_session"] = PracticeSession("alice", "Arrays")
        state["advanced_coding_editor"] = "# saved student draft"
        state["advanced_research_job"] = {"request": {"topic": "Earlier topic"}, "complete": False}
        session = state["practice_session"]
        request_navigation(state, "coding", "python recursion")
        apply_navigation(state)
        self.assertEqual(state["advanced_coding_target_concept"], "Recursion")
        request_navigation(state, "research", "Python Recursion")
        apply_navigation(state)
        self.assertEqual(state["advanced_research_concept_input"], "Python Recursion")
        self.assertIs(state["practice_session"], session)
        self.assertEqual(state["advanced_coding_editor"], "# saved student draft")
        self.assertEqual(state["advanced_research_job"]["request"]["topic"], "Earlier topic")

    def test_pending_navigation_roundtrip_and_cross_student_rejection(self):
        state = student_state("alice")
        request_navigation(state, "research", "Recursion")
        loaded = restore(capture(state), "alice", OfflineOrchestrator)
        apply_navigation(loaded)
        self.assertEqual(loaded["_app_page"], "Advanced Research Agent")
        self.assertEqual(loaded["advanced_research_topic_input"], "Recursion")
        loaded["journey_navigation"] = dict(state["journey_navigation"], user_id="bob")
        with self.assertRaisesRegex(ValueError, "another student"):
            apply_navigation(loaded)
        self.assertEqual(loaded["student"].user_id, "alice")

    def test_actual_three_agent_evidence_conflict_diagnostic_and_replanning(self):
        student, runtime = StudentCognitiveModel("alice"), orchestrator()
        service = StudentJourneyService(student, runtime)
        initial = service.observe("Recursion")
        self.assertEqual(initial["coding"].difficulty, "easy")
        session = runtime.learning_runtime.start_practice_session(student, "Python Recursion", max_questions=5).session
        for _ in range(5):
            runtime.learning_runtime.submit_practice_session_answer(student, session, "A base case")
        learned = service.observe("recursion")
        self.assertEqual(learned["attempts"], 5)
        self.assertNotEqual(learned["coding"].difficulty, initial["coding"].difficulty)
        self.assertNotEqual(learned["research"].action_type, initial["research"].action_type)
        self.assertFalse(learned["has_conflict"])

        workflow = service.coding_workflow()
        self.assertIs(workflow.student, student)
        self.assertIs(workflow.cognitive_engine, runtime.cognitive_engine)
        workflow.evaluator = catalog_tests.EvaluationGuardrailTests().evaluator()
        exercise = get_verified_exercise("Recursion", learned["coding"].difficulty)
        controller = CodingSubmissionController(workflow, exercise)
        record, is_new = controller.submit(exercise.task.starter_code)
        self.assertTrue(is_new)
        self.assertEqual(record.result.evaluation.performance, 0)
        self.assertTrue(service.observe("Python Recursion")["has_conflict"])
        self.assertEqual(controller.submit(exercise.task.starter_code)[1], False)

        quote = "Recursive calls require a stopping condition."
        abstract = ("This controlled synthetic recursion study examines how learners reason about recursive functions. "
                    + quote + " The illustrative evaluation discusses base cases and recursive steps, "
                    "tracing calls through simple examples and examining the consequences of omitting a base case. "
                    "The source describes its teaching approach, limitations of the examples, and the need for "
                    "independent assessment before drawing broader conclusions about learning outcomes.")
        source = ResearchPaper("Controlled Recursion Study", ["Fixture Author"], abstract,
                               "https://example.org/fixture/recursion", 2025, "offline_fixture", "recursion")
        summary = PaperSummary(source.title, source.authors, source.year, source.url,
                               proposed_method=quote, evidence_quotes={"proposed_method": quote})
        research = service.research_coordinator(workflow=IntegratedResearchWorkflow(
            summarizer=SimpleNamespace(summarize=lambda paper: summary)))
        outcome = research.conduct_research("Recursion", "recursion", limit=1, papers=[source], include_thematic_review=False)
        self.assertEqual(outcome.action.action_type, "diagnostic_research")
        self.assertEqual(student.get_concept("Recursion").attempts, 6)
        question = ResearchComprehensionQuestion("Recursion", "What prevents unbounded recursive calls?",
                                                 "A base case", quote)
        assessment = ResearchAssessmentService(research, generator=SimpleNamespace(generate=lambda **kwargs: question),
            evaluator=SimpleNamespace(evaluate=lambda answer: ResearchComprehensionEvaluation(
                False, 0.0, .9, "Controlled incorrect comprehension response")))
        generated = assessment.generate_question(outcome.research, "Recursion")
        assessment.submit_answer("alice", generated, "No stopping condition is needed")
        conflicted = service.observe("Python Recursion")
        self.assertEqual(conflicted["evidence_sources"], {"learning": 5, "coding": 1, "research": 1})
        self.assertTrue(conflicted["has_conflict"])
        self.assertEqual(conflicted["coding"].action_type, "diagnostic_coding")

        bridge = LearningDiagnosticBridge(student, runtime.cognitive_engine, runtime.learning_runtime)
        diagnostic = bridge.start("Recursion")
        resolved = bridge.submit_answer(diagnostic, "A base case")
        self.assertTrue(resolved.diagnostic_outcome.conflict_resolved)
        final = service.observe("recursion")
        self.assertFalse(final["has_conflict"])
        self.assertNotEqual(final["learning"].action_type, "diagnostic_quiz")
        self.assertNotEqual(final["coding"].action_type, "diagnostic_coding")
        self.assertNotEqual(final["research"].action_type, "diagnostic_research")
        self.assertEqual(final["attempts"], 8)
        self.assertEqual(len(student.concepts), 1)
        saved = student_state("alice")
        saved.update(student=student, orchestrator=runtime, advanced_coding_exercise=exercise,
                     advanced_coding_loaded_concept="Recursion", advanced_coding_controller=controller)
        loaded = restore(capture(saved), "alice", OfflineOrchestrator)
        restored = StudentJourneyService(loaded["student"], loaded["orchestrator"]).observe("Python Recursion")
        self.assertEqual(restored["attempts"], final["attempts"])
        self.assertEqual(restored["mastery"], final["mastery"])
        self.assertEqual(restored["evidence_sources"], final["evidence_sources"])
        self.assertFalse(restored["has_conflict"])
        self.assertEqual(StudentJourneyService(StudentCognitiveModel("bob"), runtime).observe("Recursion")["attempts"], 0)


if __name__ == "__main__":
    unittest.main()
