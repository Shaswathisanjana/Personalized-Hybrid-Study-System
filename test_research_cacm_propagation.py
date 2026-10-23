from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.research_agent.models import (
    ResearchComprehensionQuestion,
    ResearchComprehensionEvaluation,
)

from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)


def main():

    print("\nSTEP 1: Creating shared student model...")

    student = StudentCognitiveModel(
        user_id="synthetic_research_student"
    )

    concept = student.get_concept(
        "Deep Learning"
    )

    initial_mastery = concept.mastery
    initial_confidence = concept.confidence
    initial_attempts = concept.attempts

    print("Initial mastery:", initial_mastery)
    print("Initial confidence:", initial_confidence)
    print("Initial attempts:", initial_attempts)

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=CognitiveEngine(),
    )

    print("\nSTEP 2: Creating a comprehension question...")

    question = ResearchComprehensionQuestion(
        concept_name="Deep Learning",
        question=(
            "Why are convolutional neural networks "
            "commonly used for image classification?"
        ),
        correct_answer=(
            "CNNs learn spatial features from images "
            "using convolutional filters."
        ),
        explanation=(
            "Convolutional layers extract local patterns "
            "and increasingly complex visual features."
        ),
        difficulty="medium",
    )

    print("\nSTEP 3: Simulating an evaluated student answer...")

    evaluation = ResearchComprehensionEvaluation(
        is_correct=True,
        performance=0.90,
        confidence=0.85,
        feedback=(
            "The student demonstrated a good understanding "
            "of convolutional feature extraction."
        ),
        detected_misconceptions=[],
    )

    print("\nSTEP 4: Sending Research Agent evidence into CACM...")

    outcome = coordinator.submit_comprehension_evaluation(
        user_id=student.user_id,
        question=question,
        evaluation=evaluation,
    )

    updated = student.get_concept(
        "Deep Learning"
    )

    print("\n========== CACM RESULT ==========")
    print("Source agent: research")
    print("Performance:", outcome.performance)
    print("Evaluation confidence:", outcome.confidence)
    print("Initial mastery:", initial_mastery)
    print("Updated mastery:", updated.mastery)
    print("Initial attempts:", initial_attempts)
    print("Updated attempts:", updated.attempts)
    print("Active conflict:", outcome.has_active_conflict)

    print("\nSTEP 5: Validating cognitive propagation...")

    assert outcome.concept_name == "Deep Learning"
    assert outcome.performance == 0.90

    assert updated.attempts == initial_attempts + 1, (
        "CACM did not record the research comprehension attempt."
    )

    assert updated.mastery != initial_mastery, (
        "CACM did not update mastery after assessed evidence."
    )

    assert coordinator.cacm_runtime.student is student, (
        "The coordinator is not using the shared student model."
    )

    print(
        "\nTEST PASSED: Research comprehension evidence "
        "successfully updated the shared CACM cognitive model."
    )


if __name__ == "__main__":
    main()
