from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence

from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)
from app.research_agent.research_workflow import ResearchWorkflowResult


class MockResearchWorkflow:

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

        return ResearchWorkflowResult(topic=topic)


def main():

    student = StudentCognitiveModel(
        user_id="planner_integration_test"
    )

    workflow = MockResearchWorkflow()
    engine = CognitiveEngine()

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=engine,
        workflow=workflow,
    )

    result = coordinator.conduct_research(
        topic="Deep Learning for Medical Images",
        concept_name="Deep Learning",
        limit=3,
        papers=[],
        include_thematic_review=False,
    )

    assert result.plan is not None
    assert result.plan.is_new_concept is True
    assert result.action.action_type == "introductory_research"
    assert result.action.difficulty == "easy"

    assert len(workflow.calls) == 1
    assert workflow.calls[0]["topic"] == result.plan.topic
    assert workflow.calls[0]["limit"] == 3
    assert workflow.calls[0]["papers"] == []
    assert workflow.calls[0]["include_thematic_review"] is False

    print("PASS: Planner integrated with coordinator.")
    print("Selected action:", result.action.action_type)
    print("Research goal:", result.plan.research_goal)

    state = student.get_concept("Deep Learning")

    assert state.attempts == 0
    assert state.mastery == 0.5

    print("PASS: Research generation does not update CACM.")

    # Create actual contradictory observations in the shared CACM
    # engine. An artificial conflict flag alone is no longer accepted.
    engine.process_evidence(
        student,
        LearningEvidence(
            user_id=student.user_id,
            concept_name="Deep Learning",
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
            concept_name="Deep Learning",
            source_agent="coding",
            evidence_type="coding_solution",
            performance=0.15,
            difficulty=0.70,
            reliability=0.90,
        ),
    )

    assert engine.has_conflict(student.user_id, "Deep Learning")
    print("PASS: Genuine cross-agent conflict established.")

    attempts_before = state.attempts
    mastery_before = state.mastery

    result = coordinator.conduct_research(
        topic="Deep Learning for Medical Images",
        concept_name="Deep Learning",
        papers=[],
    )

    assert result.action.action_type == "diagnostic_research"
    assert result.plan.action.action_type == "diagnostic_research"

    print("PASS: Real cross-agent conflict selects diagnostic research.")

    assert state.attempts == attempts_before
    assert state.mastery == mastery_before
    assert engine.has_conflict(student.user_id, "Deep Learning")

    print("PASS: Diagnostic planning does not fabricate assessment evidence.")

    print()
    print("ALL COORDINATOR INTEGRATION TESTS PASSED.")


if __name__ == "__main__":
    main()
