from __future__ import annotations

from app.cognitive.cross_agent_runtime import (
    CrossAgentRuntime,
    CrossAgentDecision,
    CrossAgentResolutionOutcome,
)
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
    DiagnosticSession,
)
from app.cognitive.models import StudentCognitiveModel


class ResearchDiagnosticBridge:
    """
    Connects Research Agent diagnostic recommendations
    to the existing shared CACM diagnostic workflow.

    Research does not independently manufacture or
    resolve cognitive conflicts.
    """

    def __init__(
        self,
        student: StudentCognitiveModel,
        cognitive_engine: CognitiveEngine,
        cross_agent_runtime: CrossAgentRuntime | None = None,
    ):
        self.student = student
        self.cognitive_engine = cognitive_engine

        if cross_agent_runtime is None:
            intervention = DiagnosticIntervention(
                cognitive_engine=cognitive_engine,
            )

            cross_agent_runtime = CrossAgentRuntime(
                cognitive_engine=cognitive_engine,
                diagnostic_intervention=intervention,
            )

        if cross_agent_runtime.cognitive_engine is not cognitive_engine:
            raise ValueError(
                "Diagnostic runtime must use the shared CACM engine."
            )

        self.runtime = cross_agent_runtime

    def start(self, concept_name: str) -> CrossAgentDecision:
        """
        Start an existing CACM diagnostic intervention
        only when the shared engine has a real conflict.
        """

        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError("Concept name cannot be empty.")

        if not self.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=concept_name,
        ):
            raise ValueError(
                "Cannot start Research diagnostic intervention: "
                "no genuine unresolved CACM conflict exists."
            )

        decision = self.runtime.decide(
            student=self.student,
            concept_name=concept_name,
        )

        if decision.diagnostic_session is None:
            raise RuntimeError(
                "CACM detected a conflict but did not create "
                "a diagnostic session."
            )

        return decision

    def submit_answer(
        self,
        session: DiagnosticSession,
        answer: str,
    ) -> CrossAgentResolutionOutcome:
        """
        Forward the student's answer to the existing
        diagnostic evaluator and CACM conflict resolver.
        """

        if session.user_id != self.student.user_id:
            raise ValueError(
                "Diagnostic session belongs to a different student."
            )

        if not answer.strip():
            raise ValueError(
                "Enter a diagnostic answer before submitting."
            )

        if (self.student.user_id, "diagnostic:" + session.session_id) not in self.cognitive_engine.assessment_records and not self.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=session.concept_name,
        ):
            raise ValueError(
                "No unresolved CACM conflict remains for this session."
            )

        return self.runtime.submit_diagnostic_and_replan(
            student=self.student,
            session=session,
            answer=answer.strip(),
        )
