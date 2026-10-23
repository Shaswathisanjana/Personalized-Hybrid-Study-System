from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.cross_agent_runtime import CrossAgentRuntime
from app.cognitive.diagnostic_intervention import DiagnosticIntervention
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel
from app.research_agent.diagnostic_bridge import ResearchDiagnosticBridge

from test_research_diagnostic_bridge import (
    MockQuizGenerator,
    MockAnswerEvaluator,
)


def main():
    concept = "Recursion"
    student = StudentCognitiveModel(
        user_id="research_diagnostic_ui_test"
    )
    engine = CognitiveEngine()

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
    print("PASS: Genuine conflict established.")

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

    # This temporary test entrypoint renders only the existing
    # diagnostic component. No project UI code is modified.
    entrypoint = """
import streamlit as st
from app.research_agent.streamlit_diagnostic import (
    display_research_diagnostic,
)

display_research_diagnostic(
    concept_name="Recursion",
    student=st.session_state.test_student,
    orchestrator=st.session_state.test_orchestrator,
)
"""

    app = AppTest.from_string(
        entrypoint,
        default_timeout=15,
    )

    app.session_state["test_student"] = student
    app.session_state["test_orchestrator"] = (
        SimpleNamespace(cognitive_engine=engine)
    )

    # Inject the already configured mock bridge, avoiding Gemini.
    app.session_state["research_diagnostic_bridge"] = bridge
    app.session_state["research_diagnostic_student_id"] = student.user_id
    app.session_state["research_diagnostic_engine"] = engine
    app.session_state["research_diagnostic_session"] = None
    app.session_state["research_diagnostic_concept"] = None
    app.session_state["research_diagnostic_outcome"] = None

    app.run()

    assert not app.exception, app.exception
    assert any(
        "Cross-Agent Diagnostic Intervention" in item.value
        for item in app.subheader
    )
    assert any(
        "Generate CACM Diagnostic Question" in item.label
        for item in app.button
    )
    print("PASS: Diagnostic section and Generate button rendered.")

    app.button(
        key="generate_research_diagnostic"
    ).click().run()

    assert not app.exception, app.exception
    assert any(
        "Explain the base case in recursion." in item.value
        for item in app.markdown
    )
    print("PASS: Mock diagnostic question rendered.")

    # Locate widgets using their actual displayed labels rather
    # than assuming Streamlit's internally generated form keys.
    answer_fields = [
        item for item in app.text_area
        if item.label == "Your diagnostic answer"
    ]

    assert len(answer_fields) == 1, (
        "Expected exactly one diagnostic answer field."
    )

    answer_fields[0].input("The stopping condition.").run()

    submit_buttons = [
        item for item in app.button
        if item.label == "Submit Diagnostic Answer"
    ]

    assert len(submit_buttons) == 1, (
        "Expected exactly one diagnostic submit button."
    )

    submit_buttons[0].click().run()

    assert not app.exception, app.exception
    assert not engine.has_conflict(student.user_id, concept)
    print("PASS: Diagnostic answer resolved the CACM conflict.")

    visible = "\n".join(
        str(item.value)
        for collection in (
            app.success,
            app.warning,
            app.markdown,
            app.text,
        )
        for item in collection
    )

    assert "Diagnostic assessment completed." in visible
    assert "CACM resolved the cross-agent cognitive conflict." in visible
    assert "Updated CACM State" in visible
    assert "Learning Agent Replanning" in visible

    print("PASS: Completed diagnostic feedback remains visible.")
    print("PASS: Updated cognitive state and replanning rendered.")
    print()
    print("ALL STREAMLIT DIAGNOSTIC UI TESTS PASSED.")


if __name__ == "__main__":
    main()
