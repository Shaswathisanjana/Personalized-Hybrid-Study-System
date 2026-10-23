from unittest.mock import Mock

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.cross_agent_runtime import CrossAgentRuntime
from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
)
from app.cognitive.models import StudentCognitiveModel
from app.coding_agent.diagnostic_bridge import CodingDiagnosticBridge


def main():
    student = StudentCognitiveModel(user_id="coding_diagnostic_test")
    engine = CognitiveEngine()

    evaluator = Mock()
    evaluation = Mock()
    evaluation.performance = 0.95
    evaluation.detected_misconceptions = []
    evaluator.evaluate.return_value = evaluation

    generator = Mock()
    generator.generate.return_value = Mock()

    intervention = DiagnosticIntervention(
        cognitive_engine=engine,
        quiz_generator=generator,
        answer_evaluator=evaluator,
    )

    runtime = CrossAgentRuntime(
        cognitive_engine=engine,
        diagnostic_intervention=intervention,
    )

    bridge = CodingDiagnosticBridge(
        student=student,
        cognitive_engine=engine,
        cross_agent_runtime=runtime,
    )

    # TEST 1: No artificial conflicts.
    try:
        bridge.start("Recursion")
        raise AssertionError("Diagnostic started without a real conflict.")
    except ValueError:
        print("PASS 1: No-conflict diagnostic rejected.")

    # Set up an active conflict for this isolated bridge test.
    # The conflict object itself is simulated; this test checks
    # orchestration, not the conflict detector's mathematics.
    engine.active_conflicts[(student.user_id, "Recursion")] = [Mock()]

    decision = bridge.start("Recursion")
    session = decision.diagnostic_session

    assert session is not None
    assert session.user_id == student.user_id
    print("PASS 2: Active-conflict diagnostic session created.")

    # TEST 3: A different student's session must be rejected.
    from dataclasses import replace

    foreign_session = replace(
        session,
        user_id="another_student",
    )

    try:
        bridge.submit_answer(foreign_session, "A diagnostic answer")
        raise AssertionError("Foreign session was accepted.")
    except ValueError:
        print("PASS 3: Foreign diagnostic session rejected.")

    # Make the resolver report a successful resolution.
    resolution = Mock()
    resolution.resolved = True
    engine.conflict_resolver.resolve = Mock(return_value=resolution)

    first = bridge.submit_answer(
        session,
        "A recursive function must have a base case.",
    )

    assert first.has_active_conflict is False
    assert first.next_coding_action.action_type != "diagnostic_coding"

    attempts_after_first = student.get_concept("Recursion").attempts

    second = bridge.submit_answer(
        session,
        "A recursive function must have a base case.",
    )

    attempts_after_second = student.get_concept("Recursion").attempts

    assert attempts_after_second == attempts_after_first
    assert evaluator.evaluate.call_count == 1
    assert len(intervention.completed_sessions) == 1

    print("PASS 4: Repeated session did not update CACM twice.")
    print("PASS 5: Coding Agent replanned after conflict resolution.")
    print("ALL CODING DIAGNOSTIC BRIDGE TESTS PASSED.")


if __name__ == "__main__":
    main()
