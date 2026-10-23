import streamlit as st

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.coding_agent.streamlit_diagnostic import display_coding_diagnostic


class TestOrchestrator:
    def __init__(self):
        self.cognitive_engine = CognitiveEngine()


st.set_page_config(
    page_title="Isolated Coding Diagnostic Test",
    layout="wide",
)

st.title("Isolated Coding Diagnostic UI Test")

st.info(
    "TEST ONLY: This page uses simulated assessment evidence "
    "and a separate student. It does not modify the main app's "
    "student progress."
)

if "isolated_diagnostic_student" not in st.session_state:
    student = StudentCognitiveModel(
        user_id="isolated_diagnostic_ui_student"
    )

    orchestrator = TestOrchestrator()

    engine = orchestrator.cognitive_engine

    for agent, performance in [
        ("learning", 0.90),
        ("coding", 0.20),
    ]:
        engine.process_evidence(
            student=student,
            evidence=LearningEvidence(
                user_id=student.user_id,
                concept_name="Recursion",
                source_agent=agent,
                evidence_type=(
                    "quiz"
                    if agent == "learning"
                    else "coding_solution"
                ),
                performance=performance,
                difficulty=0.70,
                reliability=0.90,
            ),
        )

    st.session_state.isolated_diagnostic_student = student
    st.session_state.isolated_diagnostic_orchestrator = orchestrator

student = st.session_state.isolated_diagnostic_student
orchestrator = st.session_state.isolated_diagnostic_orchestrator

st.write(
    "**Active Recursion conflict:**",
    orchestrator.cognitive_engine.has_conflict(
        student.user_id,
        "Recursion",
    ),
)

display_coding_diagnostic(
    student=student,
    orchestrator=orchestrator,
)
