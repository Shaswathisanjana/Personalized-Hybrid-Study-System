from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine

from app.learning_agent.agent import LearningAgent
from app.learning_agent.executor import (
    LearningActionExecutor,
    LearningActivity,
)


class LearningAgentRuntime:
    """
    Controls the complete Learning Agent cycle:

    Observe -> Decide -> Execute -> Receive Evidence
    -> Update Cognitive State -> Re-plan
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
    ):
        self.cognitive_engine = cognitive_engine
        self.agent = LearningAgent()
        self.executor = LearningActionExecutor()

    def get_next_activity(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> LearningActivity:
        """
        Observe the student's cognitive state,
        choose the next action and execute it.
        """

        has_conflict = self.cognitive_engine.has_conflict(
            student.user_id,
            concept_name,
        )

        action = self.agent.choose_action(
            student=student,
            concept_name=concept_name,
            has_conflict=has_conflict,
        )

        activity = self.executor.execute(action)

        return activity

    def submit_performance(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        performance: float,
        evidence_type: str,
        difficulty: float,
        reliability: float,
    ):
        """
        Convert student performance into evidence
        and update the shared cognitive model.
        """

        evidence = LearningEvidence(
            user_id=student.user_id,
            concept_name=concept_name,
            source_agent="learning",
            evidence_type=evidence_type,
            performance=performance,
            difficulty=difficulty,
            reliability=reliability,
        )

        result = self.cognitive_engine.process_evidence(
            student=student,
            evidence=evidence,
        )

        return result

    def submit_and_replan(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        performance: float,
        evidence_type: str,
        difficulty: float,
        reliability: float,
    ):
        """
        Process performance and automatically
        choose the next personalized activity.
        """

        cognitive_result = self.submit_performance(
            student=student,
            concept_name=concept_name,
            performance=performance,
            evidence_type=evidence_type,
            difficulty=difficulty,
            reliability=reliability,
        )

        next_activity = self.get_next_activity(
            student=student,
            concept_name=concept_name,
        )

        return {
            "cognitive_result": cognitive_result,
            "next_activity": next_activity,
        }