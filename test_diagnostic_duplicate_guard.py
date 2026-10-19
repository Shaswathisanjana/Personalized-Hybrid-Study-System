from unittest.mock import Mock

from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
    DiagnosticSession,
)
from app.cognitive.models import StudentCognitiveModel


def main():
    student = StudentCognitiveModel(user_id="diagnostic_test_student")

    engine = Mock()
    engine.has_conflict.return_value = True
    engine.process_evidence.return_value = {
        "conflict_resolved": True,
        "has_active_conflict": False,
        "resolution_results": [],
    }

    evaluation = Mock()
    evaluation.performance = 0.9
    evaluation.detected_misconceptions = []

    evaluator = Mock()
    evaluator.evaluate.return_value = evaluation

    intervention = DiagnosticIntervention(
        cognitive_engine=engine,
        quiz_generator=Mock(),
        answer_evaluator=evaluator,
    )

    session = DiagnosticSession(
        user_id=student.user_id,
        concept_name="Recursion",
        question=Mock(),
        difficulty="medium",
    )

    first = intervention.submit_answer(
        student=student,
        session=session,
        answer="My first diagnostic answer",
    )

    second = intervention.submit_answer(
        student=student,
        session=session,
        answer="My first diagnostic answer",
    )

    assert first is second, "Repeated submission must return cached outcome."
    assert evaluator.evaluate.call_count == 1, "Answer evaluated more than once."
    assert engine.process_evidence.call_count == 1, "CACM updated more than once."
    assert len(intervention.completed_sessions) == 1

    print("PASS: First submission evaluated successfully.")
    print("PASS: Repeated submission returned cached outcome.")
    print("PASS: Diagnostic evaluator called exactly once.")
    print("PASS: CACM evidence submitted exactly once.")
    print("PASS: Duplicate diagnostic safeguard verified.")


if __name__ == "__main__":
    main()
