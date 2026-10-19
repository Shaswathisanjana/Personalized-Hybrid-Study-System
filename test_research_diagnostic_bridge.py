from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.cross_agent_runtime import CrossAgentRuntime
from app.cognitive.diagnostic_intervention import DiagnosticIntervention
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult
from app.research_agent.diagnostic_bridge import ResearchDiagnosticBridge


class MockQuizGenerator:
    def generate(self, **kwargs):
        return QuizQuestion(
            concept_name=kwargs["concept_name"],
            difficulty=kwargs["difficulty"],
            question="Explain the base case in recursion.",
            correct_answer="It is the stopping condition.",
            explanation="A base case stops further recursive calls.",
        )


class MockAnswerEvaluator:
    def evaluate(self, student_answer):
        assert student_answer.answer == "The stopping condition."
        return EvaluationResult(
            is_correct=True,
            performance=0.90,
            feedback="Correct explanation of the base case.",
            detected_misconceptions=[],
        )


def main():
    student = StudentCognitiveModel(user_id="diagnostic_bridge_test")
    engine = CognitiveEngine()

    intervention = DiagnosticIntervention(
        cognitive_engine=engine,
        quiz_generator=MockQuizGenerator(),
        answer_evaluator=MockAnswerEvaluator(),
    )

    runtime = CrossAgentRuntime(
        cognitive_engine=engine,
        diagnostic_intervention=intervention,
    )

    bridge = ResearchDiagnosticBridge(
        student=student,
        cognitive_engine=engine,
        cross_agent_runtime=runtime,
    )

    concept = "Recursion"

    # No conflict: diagnostic intervention must be rejected.
    try:
        bridge.start(concept)
    except ValueError as exc:
        assert "no genuine unresolved" in str(exc)
        print("PASS: Diagnostic rejected without a real conflict.")
    else:
        raise AssertionError("Diagnostic started without a conflict.")

    # Simulated Learning Agent and Coding Agent observations.
    engine.process_evidence(
        student,
        LearningEvidence(
            user_id=student.user_id,
            concept_name=concept,
            source_agent="learning",
            evidence_type="quiz",
            performance=0.95,
            difficulty=0.70,
            reliability=0.90,
        ),
    )

    engine.process_evidence(
        student,
        LearningEvidence(
            user_id=student.user_id,
            concept_name=concept,
            source_agent="coding",
            evidence_type="coding_solution",
            performance=0.15,
            difficulty=0.70,
            reliability=0.90,
        ),
    )

    assert engine.has_conflict(student.user_id, concept)
    print("PASS: Genuine cross-agent conflict detected.")

    attempts_before = student.get_concept(concept).attempts

    decision = bridge.start(concept)
    session = decision.diagnostic_session

    assert session is not None
    assert session.concept_name == concept
    assert session.question.question
    assert student.get_concept(concept).attempts == attempts_before
    assert engine.has_conflict(student.user_id, concept)

    print("PASS: Existing CACM diagnostic session generated.")
    print("Question:", session.question.question)
    print("PASS: Generating a question did not update mastery.")

    try:
        bridge.submit_answer(session, "   ")
    except ValueError:
        print("PASS: Empty diagnostic answer rejected.")
    else:
        raise AssertionError("Empty answer was accepted.")

    outcome = bridge.submit_answer(
        session=session,
        answer="The stopping condition.",
    )

    assert outcome.diagnostic_outcome.evidence.evidence_type == "diagnostic_quiz"
    assert outcome.diagnostic_outcome.evidence.performance == 0.90
    assert outcome.diagnostic_outcome.conflict_resolved
    assert not outcome.diagnostic_outcome.has_active_conflict
    assert not engine.has_conflict(student.user_id, concept)
    assert student.get_concept(concept).attempts == attempts_before + 1
    assert outcome.next_action is not None

    print("PASS: Evaluated answer produced diagnostic_quiz evidence.")
    print("PASS: Existing CACM Conflict Resolver resolved the disagreement.")
    print("PASS: Learning Agent replanned after diagnostic evaluation.")
    print("Next action:", outcome.next_action.action_type)

    print()
    print("ALL RESEARCH DIAGNOSTIC BRIDGE TESTS PASSED.")


if __name__ == "__main__":
    main()
