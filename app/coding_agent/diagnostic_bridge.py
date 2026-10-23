from __future__ import annotations

from dataclasses import dataclass

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.cross_agent_runtime import (
    CrossAgentRuntime,
    CrossAgentDecision,
    CrossAgentResolutionOutcome,
)
from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
    DiagnosticSession,
)
from app.cognitive.models import StudentCognitiveModel
from app.coding_agent.agent import CodingAgent, CodingAction


@dataclass
class CodingDiagnosticOutcome:
    resolution: CrossAgentResolutionOutcome
    next_coding_action: CodingAction
    has_active_conflict: bool


class CodingDiagnosticBridge:
    """
    Reuses the shared CACM diagnostic workflow for Coding Agent.

    Only genuine unresolved cross-agent conflicts can start
    diagnostic intervention. Evaluated diagnostic evidence is
    processed by the existing shared CognitiveEngine.
    """

    def __init__(
        self,
        student: StudentCognitiveModel,
        cognitive_engine: CognitiveEngine,
        cross_agent_runtime: CrossAgentRuntime | None = None,
        coding_agent: CodingAgent | None = None,
    ):
        if not isinstance(student, StudentCognitiveModel):
            raise TypeError("student must be a StudentCognitiveModel.")

        if not isinstance(cognitive_engine, CognitiveEngine):
            raise TypeError("cognitive_engine must be a CognitiveEngine.")

        self.student = student
        self.cognitive_engine = cognitive_engine
        self.coding_agent = (
            coding_agent if coding_agent is not None else CodingAgent()
        )

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

        if (
            cross_agent_runtime.diagnostic_intervention.cognitive_engine
            is not cognitive_engine
        ):
            raise ValueError(
                "Diagnostic intervention must use the shared CACM engine."
            )

        self.runtime = cross_agent_runtime

    def start(self, concept_name: str) -> CrossAgentDecision:
        """Start a diagnostic only when CACM has a genuine conflict."""

        if not isinstance(concept_name, str) or not concept_name.strip():
            raise ValueError("Concept name cannot be empty.")

        concept_name = concept_name.strip()

        if not self.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=concept_name,
        ):
            raise ValueError(
                "Cannot start Coding diagnostic: "
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
    ) -> CodingDiagnosticOutcome:
        """
        Evaluate the real diagnostic answer through shared CACM,
        then recalculate the Coding Agent's next recommendation.
        """

        if not isinstance(session, DiagnosticSession):
            raise TypeError("session must be a DiagnosticSession.")

        if session.user_id != self.student.user_id:
            raise ValueError(
                "Diagnostic session belongs to a different student."
            )

        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Enter a diagnostic answer before submitting.")

        intervention = self.runtime.diagnostic_intervention

        # A completed session is safe to replay: the shared
        # intervention returns its cached outcome without
        # submitting evidence again.
        already_completed = (
            session.session_id in intervention.completed_sessions
        )

        if not already_completed and (self.student.user_id, "diagnostic:" + session.session_id) not in self.cognitive_engine.assessment_records and not self.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=session.concept_name,
        ):
            raise ValueError(
                "No unresolved CACM conflict remains for this session."
            )

        resolution = self.runtime.submit_diagnostic_and_replan(
            student=self.student,
            session=session,
            answer=answer.strip(),
        )

        has_conflict = self.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=session.concept_name,
        )

        next_action = self.coding_agent.choose_action(
            student=self.student,
            concept_name=session.concept_name,
            has_active_conflict=has_conflict,
        )

        return CodingDiagnosticOutcome(
            resolution=resolution,
            next_coding_action=next_action,
            has_active_conflict=has_conflict,
        )
