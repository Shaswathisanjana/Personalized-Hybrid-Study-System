from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine

from app.learning_agent.agent import LearningAgent

from app.learning_agent.executor import (
    LearningActionExecutor,
    LearningActivity,
)

from app.learning_agent.content_generator import (
    PersonalizedContentGenerator,
    GeneratedContent,
)

from app.learning_agent.content_provider import (
    ContentProvider,
    LocalContentProvider,
)


class LearningAgentRuntime:
    """
    Runtime controller for the complete Learning Agent cycle.

    Flow:
        Observe cognitive state
        -> Decide pedagogical action
        -> Build personalized content request
        -> Generate actual learning content
        -> Execute activity
        -> Receive student performance
        -> Update cognitive model
        -> Re-plan
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
        content_provider: ContentProvider | None = None,
    ):
        self.cognitive_engine = cognitive_engine

        # Decides WHAT the student should do next
        self.agent = LearningAgent()

        # Converts the selected action into
        # an executable learning activity
        self.executor = LearningActionExecutor()

        # Builds a personalized request using
        # the student's cognitive state
        self.content_generator = (
            PersonalizedContentGenerator()
        )

        # Generates the actual student-facing content.
        #
        # For now we use LocalContentProvider.
        # Later we can replace it with GeminiContentProvider.
        self.content_provider = (
            content_provider
            if content_provider is not None
            else LocalContentProvider()
        )

    # ==================================================
    # 1. OBSERVE -> DECIDE
    # ==================================================

    def choose_action(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ):
        """
        Observe the student's shared cognitive state
        and decide the next pedagogical action.
        """

        # Check whether Learning, Coding, or Research
        # agents currently disagree about this concept.
        has_conflict = self.cognitive_engine.has_conflict(
            student.user_id,
            concept_name,
        )

        # Learning Agent decides what should happen next.
        action = self.agent.choose_action(
            student=student,
            concept_name=concept_name,
            has_conflict=has_conflict,
        )

        return action

    # ==================================================
    # 2. BUILD PERSONALIZED CONTENT REQUEST
    # ==================================================

    def generate_personalized_content(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> GeneratedContent:
        """
        Use the cognitive state and Learning Agent decision
        to build a personalized content request.
        """

        action = self.choose_action(
            student=student,
            concept_name=concept_name,
        )

        generated_content = (
            self.content_generator.generate(
                student=student,
                action=action,
            )
        )

        return generated_content

    # ==================================================
    # 3. OBSERVE -> DECIDE -> GENERATE -> EXECUTE
    # ==================================================

    def get_next_activity(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> LearningActivity:
        """
        Complete Learning Agent execution.

        1. Observe cognitive state
        2. Select pedagogical action
        3. Build personalized content request
        4. Generate actual educational content
        5. Return executable activity
        """

        # ----------------------------------------------
        # STEP 1 + 2
        # Observe student and choose action
        # ----------------------------------------------

        action = self.choose_action(
            student=student,
            concept_name=concept_name,
        )

        # ----------------------------------------------
        # STEP 3
        # Build cognitively personalized request
        # ----------------------------------------------

        generated_request = (
            self.content_generator.generate(
                student=student,
                action=action,
            )
        )

        # ----------------------------------------------
        # STEP 4
        # Generate actual student-facing content
        # ----------------------------------------------

        actual_content = (
            self.content_provider.create_content(
                generated_request
            )
        )

        # ----------------------------------------------
        # STEP 5
        # Convert action into executable activity
        # ----------------------------------------------

        activity = self.executor.execute(
            action
        )

        # Executor initially creates generic content.
        # Replace it with personalized content generated
        # by our selected ContentProvider.
        activity.content = actual_content

        return activity

    # ==================================================
    # 4. RECEIVE STUDENT PERFORMANCE
    # ==================================================

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
        Convert student performance into LearningEvidence
        and send it to the shared CognitiveEngine.
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

        # Cognitive Engine updates:
        # - mastery
        # - confidence
        # - attempts
        # - conflict state
        result = self.cognitive_engine.process_evidence(
            student=student,
            evidence=evidence,
        )

        return result

    # ==================================================
    # 5. UPDATE -> AUTOMATIC RE-PLANNING
    # ==================================================

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
        Process new student performance and immediately
        determine the next personalized activity.

        This completes the agent loop:

        performance
            -> evidence
            -> cognitive update
            -> observe new state
            -> re-plan
            -> generate next activity
        """

        # Update shared cognitive state
        cognitive_result = self.submit_performance(
            student=student,
            concept_name=concept_name,
            performance=performance,
            evidence_type=evidence_type,
            difficulty=difficulty,
            reliability=reliability,
        )

        # Automatically observe updated state
        # and decide what the student needs next.
        next_activity = self.get_next_activity(
            student=student,
            concept_name=concept_name,
        )

        return {
            "cognitive_result": cognitive_result,
            "next_activity": next_activity,
        }