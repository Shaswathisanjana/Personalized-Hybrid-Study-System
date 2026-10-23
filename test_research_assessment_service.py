from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.research_agent.assessment_service import (
    ResearchAssessmentService,
)
from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)
from app.research_agent.models import (
    ResearchComprehensionQuestion,
    ResearchComprehensionEvaluation,
)
from app.research_agent.paper_summarizer import PaperSummary
from app.research_agent.research_workflow import ResearchWorkflowResult


class MockGenerator:

    def generate(self, synthesis, concept_name, difficulty):

        assert synthesis.evidence

        return ResearchComprehensionQuestion(
            concept_name=concept_name,
            question="What is the purpose of the proposed method?",
            correct_answer="To classify medical images.",
            explanation=(
                "The supported finding describes medical "
                "image classification."
            ),
            difficulty=difficulty,
        )


class MockEvaluator:

    def evaluate(self, student_answer):

        assert student_answer.answer.strip()

        return ResearchComprehensionEvaluation(
            is_correct=True,
            performance=0.9,
            confidence=0.8,
            feedback="The answer demonstrates understanding.",
        )


def main():

    student = StudentCognitiveModel(user_id="student_001")
    engine = CognitiveEngine()

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=engine,
    )

    service = ResearchAssessmentService(
        coordinator=coordinator,
        generator=MockGenerator(),
        evaluator=MockEvaluator(),
    )

    summary = PaperSummary(
        title="Synthetic Medical Imaging Paper",
        authors=["Test Author"],
        year=2025,
        source_url="https://example.org/synthetic",
        proposed_method=(
            "A neural network classifies medical images."
        ),
        evidence_quotes={
            "proposed_method": (
                "A neural network classifies medical images."
            ),
        },
    )

    research = ResearchWorkflowResult(
        topic="Medical Image Classification",
        summaries=[summary],
    )

    concept = student.get_concept("Medical Image Classification")

    mastery_before = concept.mastery
    attempts_before = concept.attempts

    question = service.generate_question(
        result=research,
        concept_name="Medical Image Classification",
        difficulty="medium",
    )

    assert concept.mastery == mastery_before
    assert concept.attempts == attempts_before

    print("PASS: Question generation does not update mastery.")

    try:
        service.submit_answer(
            user_id=student.user_id,
            question=question,
            answer="   ",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Empty answer was accepted.")

    assert concept.attempts == attempts_before

    print("PASS: Empty answer rejected.")

    evaluation, outcome = service.submit_answer(
        user_id=student.user_id,
        question=question,
        answer="It classifies medical images.",
    )

    assert evaluation.performance == 0.9
    assert outcome.concept_name == "Medical Image Classification"
    assert concept.attempts == attempts_before + 1

    print("PASS: Assessment propagated to shared CACM state.")
    print("Mastery before:", mastery_before)
    print("Mastery after:", concept.mastery)
    print("Attempts after:", concept.attempts)

    try:
        service.submit_answer(
            user_id=student.user_id,
            question=question,
            answer="Submitting again.",
        )
    except ValueError as exc:
        assert "already been submitted" in str(exc)
    else:
        raise AssertionError("Duplicate submission was accepted.")

    assert concept.attempts == attempts_before + 1

    print("PASS: Duplicate submission blocked.")
    print("\nALL RESEARCH ASSESSMENT TESTS PASSED.")


if __name__ == "__main__":
    main()
