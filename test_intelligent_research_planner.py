from app.cognitive.models import StudentCognitiveModel
from app.research_agent.intelligent_planner import IntelligentResearchPlanner


def main():

    planner = IntelligentResearchPlanner()

    student = StudentCognitiveModel(
        user_id="planner_test_student"
    )

    # TEST 1: Completely new concept
    plan = planner.create_plan(
        student=student,
        topic="Deep Learning for Medical Images",
        concept_name="Deep Learning",
    )

    assert plan.is_new_concept is True
    assert plan.action.action_type == "introductory_research"
    assert plan.action.difficulty == "easy"
    assert len(plan.search_queries) >= 2

    state = student.get_concept("Deep Learning")
    assert state.attempts == 0

    print("PASS: New concept receives introductory research.")
    print("Selected action:", plan.action.action_type)
    print("Search queries:", plan.search_queries)

    # TEST 2: Previously assessed concept with low mastery
    state.mastery = 0.25
    state.confidence = 0.40
    state.attempts = 2

    plan = planner.create_plan(
        student=student,
        topic="Deep Learning for Medical Images",
        concept_name="Deep Learning",
    )

    assert plan.is_new_concept is False
    assert plan.action.action_type == "foundational_research"
    assert plan.action.difficulty == "easy"

    print("PASS: Low mastery receives foundational research.")

    # TEST 3: Cross-agent conflict takes priority
    plan = planner.create_plan(
        student=student,
        topic="Deep Learning for Medical Images",
        concept_name="Deep Learning",
        has_active_conflict=True,
    )

    assert plan.action.action_type == "diagnostic_research"
    assert plan.action.difficulty == "medium"
    assert "challenges and limitations" in plan.search_queries[1]

    print("PASS: Conflict triggers diagnostic research.")

    # TEST 4: Planning must not change cognitive evidence
    assert state.mastery == 0.25
    assert state.confidence == 0.40
    assert state.attempts == 2

    print("PASS: Planning does not modify cognitive state.")

    print()
    print("ALL INTELLIGENT PLANNER TESTS PASSED.")


if __name__ == "__main__":
    main()
