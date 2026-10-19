from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel
from app.coding_agent.agent import CodingAgent


def main():
    student = StudentCognitiveModel(
        user_id="real_conflict_test_student"
    )

    engine = CognitiveEngine()
    coding_agent = CodingAgent()

    concept_name = "Recursion"

    # First: assessed Learning Agent evidence.
    learning_evidence = LearningEvidence(
        user_id=student.user_id,
        concept_name=concept_name,
        source_agent="learning",
        evidence_type="quiz",
        performance=0.90,
        difficulty=0.60,
        reliability=0.80,
    )

    first_result = engine.process_evidence(
        student,
        learning_evidence,
    )

    assert first_result["has_active_conflict"] is False
    print("PASS 1: Learning evidence stored without a conflict.")

    # Second: contradictory assessed Coding Agent evidence.
    coding_evidence = LearningEvidence(
        user_id=student.user_id,
        concept_name=concept_name,
        source_agent="coding",
        evidence_type="coding_solution",
        performance=0.20,
        difficulty=0.60,
        reliability=0.80,
    )

    second_result = engine.process_evidence(
        student,
        coding_evidence,
    )

    conflicts = engine.get_conflicts(
        student.user_id,
        concept_name,
    )

    assert second_result["has_active_conflict"] is True
    assert len(conflicts) >= 1

    conflict = conflicts[0]

    assert conflict.first_agent == "learning"
    assert conflict.second_agent == "coding"
    assert abs(conflict.difference - 0.70) < 0.0001
    assert conflict.severity == "high"

    print("PASS 2: Real cross-agent conflict detected.")
    print("PASS 3: Conflict severity correctly classified as high.")

    action = coding_agent.choose_action(
        student=student,
        concept_name=concept_name,
        has_active_conflict=engine.has_conflict(
            student.user_id,
            concept_name,
        ),
    )

    assert action.action_type == "diagnostic_coding"

    print("PASS 4: Coding Agent selected diagnostic intervention.")

    print()
    print("Conflict:", conflict.first_agent, "vs", conflict.second_agent)
    print("Performance difference:", conflict.difference)
    print("Severity:", conflict.severity)
    print("Next Coding Action:", action.action_type)
    print()
    print("ALL REAL CROSS-AGENT CONFLICT TESTS PASSED.")


if __name__ == "__main__":
    main()
