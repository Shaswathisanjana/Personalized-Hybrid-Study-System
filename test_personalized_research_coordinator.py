from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.research_agent.research_workflow import (
    ResearchWorkflowResult,
)

from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)


class MockResearchWorkflow:
    """
    Offline replacement for the academic research workflow.
    Records its inputs without making network requests.
    """

    def __init__(self):
        self.calls = []

    def run(
        self,
        topic,
        limit=5,
        papers=None,
        include_thematic_review=True,
    ):
        self.calls.append({
            "topic": topic,
            "limit": limit,
            "papers": papers,
            "include_thematic_review": include_thematic_review,
        })

        return ResearchWorkflowResult(
            topic=topic,
        )


def main():

    print("\nSTEP 1: Creating a shared student model...")

    student = StudentCognitiveModel(
        user_id="synthetic_research_student"
    )

    concept = student.get_concept(
        "Deep Learning"
    )

    concept.mastery = 0.25
    concept.confidence = 0.30

    original_mastery = concept.mastery
    original_confidence = concept.confidence
    original_attempts = concept.attempts

    workflow = MockResearchWorkflow()

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=CognitiveEngine(),
        workflow=workflow,
    )

    print("\nSTEP 2: Testing personalized research selection...")

    result = coordinator.conduct_research(
        topic="Deep Learning for Medical Imaging",
        concept_name="Deep Learning",
        limit=3,
        papers=[],
        include_thematic_review=False,
    )

    print("Selected action:", result.action.action_type)
    print("Selected difficulty:", result.action.difficulty)
    print("Reason:", result.action.reason)

    assert result.action.action_type == (
        "foundational_research"
    )

    assert result.action.difficulty == "easy"

    assert result.research.topic == (
        "Deep Learning for Medical Imaging"
    )

    assert len(workflow.calls) == 1
    assert workflow.calls[0]["limit"] == 3
    assert workflow.calls[0]["papers"] == []

    print("\nSTEP 3: Checking cognitive-state safety...")

    assert concept.mastery == original_mastery
    assert concept.confidence == original_confidence
    assert concept.attempts == original_attempts

    print(
        "PASS: Generating research content did not "
        "change mastery, confidence or attempts."
    )

    print("\nSTEP 4: Testing conflict-aware selection...")

    conflict_result = coordinator.conduct_research(
        topic="Deep Learning for Medical Imaging",
        concept_name="Deep Learning",
        has_active_conflict=True,
        papers=[],
        include_thematic_review=False,
    )

    print(
        "Conflict action:",
        conflict_result.action.action_type,
    )

    assert conflict_result.action.action_type == (
        "diagnostic_research"
    )

    assert conflict_result.action.difficulty == "medium"

    assert concept.mastery == original_mastery
    assert concept.attempts == original_attempts

    print(
        "\nTEST PASSED: Research-CACM Coordinator "
        "offline integration works correctly."
    )


if __name__ == "__main__":
    main()
