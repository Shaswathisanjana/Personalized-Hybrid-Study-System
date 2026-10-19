from types import SimpleNamespace

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel
from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)


class OfflineWorkflow:
    """Avoids Gemini and OpenAlex during this integration test."""

    def __init__(self):
        self.calls = []

    def run(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            papers=[],
            accepted_papers=[],
            excluded_papers=[],
            summaries=[],
            search_attempts=[],
            warnings=[],
        )


def main():
    student = StudentCognitiveModel(
        user_id="cross_agent_diagnostic_test"
    )
    engine = CognitiveEngine()
    workflow = OfflineWorkflow()

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=engine,
        workflow=workflow,
    )

    concept = "Recursion"

    # First: verify a normal, unassessed concept.
    initial = coordinator.conduct_research(
        topic="Understanding Recursion",
        concept_name=concept,
        include_thematic_review=False,
    )

    assert initial.action.action_type == "introductory_research"
    assert not engine.has_conflict(student.user_id, concept)

    print("PASS: No conflict selects introductory research.")

    # These are simulated assessment observations for an
    # offline integration test, NOT real student results.
    learning_evidence = LearningEvidence(
        user_id=student.user_id,
        concept_name=concept,
        source_agent="learning",
        evidence_type="quiz",
        performance=0.95,
        difficulty=0.7,
        reliability=0.9,
    )

    coding_evidence = LearningEvidence(
        user_id=student.user_id,
        concept_name=concept,
        source_agent="coding",
        evidence_type="coding_solution",
        performance=0.15,
        difficulty=0.7,
        reliability=0.9,
    )

    engine.process_evidence(student, learning_evidence)
    result = engine.process_evidence(student, coding_evidence)

    assert result["has_active_conflict"]
    assert engine.has_conflict(student.user_id, concept)

    conflicts = engine.get_conflicts(student.user_id, concept)
    assert conflicts

    print("PASS: CACM detected genuine cross-agent disagreement.")
    print("Detected conflicts:", len(conflicts))

    attempts_before = student.get_concept(concept).attempts
    mastery_before = student.get_concept(concept).mastery

    # Notice: NO has_active_conflict=True is supplied.
    diagnostic = coordinator.conduct_research(
        topic="Understanding Recursion",
        concept_name=concept,
        include_thematic_review=False,
    )

    assert diagnostic.action.action_type == "diagnostic_research"
    assert diagnostic.action.difficulty == "medium"
    assert diagnostic.plan is not None
    assert "challenges and limitations" in (
        diagnostic.plan.search_queries[1]
    )

    print("PASS: Research Agent automatically selected Diagnostic Research.")
    print("Selected action:", diagnostic.action.action_type)
    print("Planned queries:", diagnostic.plan.search_queries)

    assert student.get_concept(concept).attempts == attempts_before
    assert student.get_concept(concept).mastery == mastery_before
    assert engine.has_conflict(student.user_id, concept)

    print("PASS: Research planning neither changed mastery nor resolved conflict.")

    # A caller cannot invent a conflict for an unrelated concept.
    try:
        coordinator.conduct_research(
            topic="Sorting Algorithms",
            concept_name="Sorting",
            has_active_conflict=True,
            include_thematic_review=False,
        )
    except ValueError as exc:
        assert "genuine unresolved" in str(exc)
        print("PASS: Artificial conflict flag rejected.")
    else:
        raise AssertionError("Artificial conflict flag was accepted.")

    print()
    print("ALL CROSS-AGENT DIAGNOSTIC PLANNING TESTS PASSED.")


if __name__ == "__main__":
    main()
