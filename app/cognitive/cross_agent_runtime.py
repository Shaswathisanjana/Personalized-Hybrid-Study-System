from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
    DiagnosticSession,
    DiagnosticOutcome,
)

from app.learning_agent.agent import (
    LearningAgent,
    LearningAction,
)


@dataclass
class CrossAgentDecision:
    """
    Decision made after observing the shared cognitive state.

    A conflict causes a diagnostic intervention.
    Otherwise the Learning Agent chooses the normal
    personalized learning action.
    """

    action: LearningAction
    diagnostic_session: DiagnosticSession | None


@dataclass
class CrossAgentResolutionOutcome:
    """
    Result after completing a cross-agent diagnostic
    intervention and re-planning from the updated
    cognitive state.
    """

    diagnostic_outcome: DiagnosticOutcome
    next_action: LearningAction


class CrossAgentRuntime:
    """
    Coordinates cross-agent cognitive conflict handling.

    This runtime does not replace the Learning Agent,
    Research Agent, or CognitiveEngine.

    It connects them.

    Flow:

        Evidence from multiple agents
                    ↓
             CognitiveEngine
                    ↓
             Conflict detected
                    ↓
              LearningAgent
                    ↓
            diagnostic_quiz
                    ↓
        DiagnosticIntervention
                    ↓
             Student answer
                    ↓
          Conflict resolution
                    ↓
          Updated cognitive state
                    ↓
             LearningAgent
                    ↓
              Re-planning
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
        diagnostic_intervention: DiagnosticIntervention,
    ):
        self.cognitive_engine = cognitive_engine
        self.diagnostic_intervention = diagnostic_intervention

        self.learning_agent = LearningAgent()


    # ======================================================
    # OBSERVE SHARED STATE AND DECIDE
    # ======================================================

    def decide(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> CrossAgentDecision:
        """
        Observe the shared cognitive state.

        If cross-agent conflict exists, the Learning Agent
        should request a diagnostic assessment.

        Otherwise normal personalization continues.
        """

        has_conflict = self.cognitive_engine.has_conflict(
            user_id=student.user_id,
            concept_name=concept_name,
        )

        action = self.learning_agent.choose_action(
            student=student,
            concept_name=concept_name,
            has_conflict=has_conflict,
        )

        diagnostic_session = None

        if action.action_type == "diagnostic_quiz":

            diagnostic_session = (
                self.diagnostic_intervention.start(
                    student=student,
                    concept_name=concept_name,
                )
            )

        return CrossAgentDecision(
            action=action,
            diagnostic_session=diagnostic_session,
        )


    # ======================================================
    # SUBMIT DIAGNOSTIC AND RE-PLAN
    # ======================================================

    def submit_diagnostic_and_replan(
        self,
        student: StudentCognitiveModel,
        session: DiagnosticSession,
        answer: str,
    ) -> CrossAgentResolutionOutcome:
        """
        Submit the student's diagnostic answer.

        DiagnosticIntervention:
            evaluates answer
            -> creates evidence
            -> updates CognitiveEngine
            -> attempts conflict resolution

        After that, the Learning Agent observes the
        UPDATED cognitive state and chooses what should
        happen next.
        """

        diagnostic_outcome = (
            self.diagnostic_intervention.submit_answer(
                student=student,
                session=session,
                answer=answer,
            )
        )

        has_conflict = self.cognitive_engine.has_conflict(
            user_id=student.user_id,
            concept_name=session.concept_name,
        )

        next_action = self.learning_agent.choose_action(
            student=student,
            concept_name=session.concept_name,
            has_conflict=has_conflict,
        )

        return CrossAgentResolutionOutcome(
            diagnostic_outcome=diagnostic_outcome,
            next_action=next_action,
        )