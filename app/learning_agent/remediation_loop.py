from dataclasses import dataclass

from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.cognitive.evidence import (
    LearningEvidence,
)

from app.cognitive.cognitive_engine import (
    CognitiveEngine,
)

from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
    EvaluationResult,
)

from app.learning_agent.answer_evaluator import (
    AnswerEvaluator,
)

from app.learning_agent.misconception_analyzer import (
    MisconceptionAnalyzer,
)

from app.learning_agent.remediation import (
    RemediationContext,
    create_remediation_context,
)

from app.learning_agent.remediation_generator import (
    RemediationGenerator,
)

from app.learning_agent.reassessment_generator import (
    ReassessmentGenerator,
)

from app.learning_agent.reassessment_processor import (
    ReassessmentProcessor,
    ReassessmentResult,
)

from app.learning_agent.agent import (
    LearningAgent,
    LearningAction,
)


# ============================================================
# ORIGINAL ANSWER RESULT
# ============================================================

@dataclass
class RemediationLoopResult:
    """
    Result after processing the student's original
    quiz answer.
    """

    evaluation: EvaluationResult

    detected_misconceptions: list[str]

    remediation_context: RemediationContext | None

    remediation_content: object | None

    reassessment_question: QuizQuestion | None

    cognitive_result: dict | None


# ============================================================
# COMPLETE REASSESSMENT RESULT
# ============================================================

@dataclass
class AdaptiveReassessmentResult:
    """
    Result after the student completes the targeted
    reassessment.

    This combines:

    - reassessment evaluation
    - cognitive update
    - misconception update
    - Learning Agent replanning
    """

    reassessment_result: ReassessmentResult

    next_action: LearningAction

    has_active_conflict: bool

    mastery: float

    confidence: float

    attempts: int


# ============================================================
# REMEDIATION LOOP
# ============================================================

class RemediationLoop:
    """
    Coordinates the complete adaptive misconception
    remediation cycle.

    Complete flow:

        Student answers quiz
                ↓
        Answer evaluation
                ↓
        Misconception analysis
                ↓
        Learning evidence
                ↓
        Shared CognitiveEngine
                ↓
        Grounded remediation
                ↓
        Targeted reassessment
                ↓
        Reassessment evaluation
                ↓
        Shared cognitive model updated again
                ↓
        Learning Agent replans next action

    The same CognitiveEngine instance is used throughout
    the complete cycle.
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine | None = None,
    ):

        # ------------------------------------------------
        # SHARED COGNITIVE ENGINE
        # ------------------------------------------------

        self.cognitive_engine = (
            cognitive_engine
            if cognitive_engine is not None
            else CognitiveEngine()
        )


        # ------------------------------------------------
        # COMPONENTS
        # ------------------------------------------------

        self.answer_evaluator = (
            AnswerEvaluator()
        )


        self.misconception_analyzer = (
            MisconceptionAnalyzer()
        )


        self.remediation_generator = (
            RemediationGenerator()
        )


        self.reassessment_generator = (
            ReassessmentGenerator()
        )


        # IMPORTANT:
        # Pass the SAME cognitive engine to the
        # ReassessmentProcessor.
        #
        # This prevents creation of a second independent
        # student cognitive state.

        self.reassessment_processor = (
            ReassessmentProcessor(
                cognitive_engine=(
                    self.cognitive_engine
                )
            )
        )


        self.learning_agent = (
            LearningAgent()
        )


    # ========================================================
    # PROCESS ORIGINAL ANSWER
    # ========================================================

    def process_answer(
        self,
        student: StudentCognitiveModel,
        student_answer: StudentAnswer,
    ) -> RemediationLoopResult:
        """
        Process the student's original quiz answer.

        Correct answer:
            update cognitive state and finish.

        Incorrect answer:
            analyze misconception,
            update cognitive state,
            generate grounded remediation,
            generate targeted reassessment.
        """

        # ------------------------------------------------
        # STEP 1: VALIDATE USER
        # ------------------------------------------------

        if (
            student.user_id
            != student_answer.user_id
        ):

            raise ValueError(
                "StudentAnswer user_id does not "
                "match StudentCognitiveModel user_id."
            )


        # ------------------------------------------------
        # STEP 2: EVALUATE ANSWER
        # ------------------------------------------------

        evaluation = (
            self.answer_evaluator.evaluate(
                student_answer
            )
        )


        question = (
            student_answer.question
        )


        concept_name = (
            question.concept_name
        )


        # ====================================================
        # CORRECT ORIGINAL ANSWER
        # ====================================================

        if evaluation.is_correct:

            evidence = LearningEvidence(
                user_id=student.user_id,

                concept_name=concept_name,

                source_agent="learning",

                evidence_type="quiz",

                performance=1.0,

                difficulty=(
                    self._difficulty_to_float(
                        question.difficulty
                    )
                ),

                reliability=0.7,

                detected_misconceptions=[],
            )


            cognitive_result = (
                self.cognitive_engine
                .process_evidence(
                    student=student,
                    evidence=evidence,
                )
            )


            return RemediationLoopResult(
                evaluation=evaluation,

                detected_misconceptions=[],

                remediation_context=None,

                remediation_content=None,

                reassessment_question=None,

                cognitive_result=(
                    cognitive_result
                ),
            )


        # ====================================================
        # INCORRECT ORIGINAL ANSWER
        # ====================================================

        detected_misconceptions = (
            self.misconception_analyzer
            .analyze(
                student_answer
            )
        )


        # ------------------------------------------------
        # CREATE NEGATIVE LEARNING EVIDENCE
        # ------------------------------------------------

        evidence = LearningEvidence(
            user_id=student.user_id,

            concept_name=concept_name,

            source_agent="learning",

            evidence_type="quiz",

            performance=0.0,

            difficulty=(
                self._difficulty_to_float(
                    question.difficulty
                )
            ),

            reliability=0.7,

            detected_misconceptions=(
                detected_misconceptions
            ),
        )


        # ------------------------------------------------
        # UPDATE SHARED COGNITIVE MODEL
        # ------------------------------------------------

        cognitive_result = (
            self.cognitive_engine
            .process_evidence(
                student=student,
                evidence=evidence,
            )
        )


        # ------------------------------------------------
        # WRONG ANSWER BUT UNKNOWN CAUSE
        # ------------------------------------------------
        #
        # We still update mastery because the student
        # answered incorrectly.
        #
        # But we do NOT invent a misconception.
        # ------------------------------------------------

        if not detected_misconceptions:

            return RemediationLoopResult(
                evaluation=evaluation,

                detected_misconceptions=[],

                remediation_context=None,

                remediation_content=None,

                reassessment_question=None,

                cognitive_result=(
                    cognitive_result
                ),
            )


        # ------------------------------------------------
        # BUILD GROUNDED REMEDIATION CONTEXT
        # ------------------------------------------------

        remediation_context = (
            create_remediation_context(
                student_answer=student_answer,

                detected_misconceptions=(
                    detected_misconceptions
                ),
            )
        )


        # ------------------------------------------------
        # GENERATE ACTUAL STUDENT-FACING REMEDIATION
        # ------------------------------------------------

        remediation_content = (
            self.remediation_generator.generate(
                student=student,

                context=remediation_context,
            )
        )


        # ------------------------------------------------
        # SELECT MISCONCEPTION TO REASSESS
        # ------------------------------------------------
        #
        # For the current prototype we use the first
        # supported misconception.
        #
        # Later this can be replaced with confidence-based
        # misconception prioritization.
        # ------------------------------------------------

        target_misconception = (
            detected_misconceptions[0]
        )


        # ------------------------------------------------
        # GENERATE NEW TARGETED REASSESSMENT
        # ------------------------------------------------

        reassessment_question = (
            self.reassessment_generator.generate(
                concept_name=concept_name,

                misconception=(
                    target_misconception
                ),

                previous_question=(
                    question.question
                ),
            )
        )


        # ------------------------------------------------
        # RETURN FIRST HALF OF ADAPTIVE CYCLE
        # ------------------------------------------------

        return RemediationLoopResult(
            evaluation=evaluation,

            detected_misconceptions=(
                detected_misconceptions
            ),

            remediation_context=(
                remediation_context
            ),

            remediation_content=(
                remediation_content
            ),

            reassessment_question=(
                reassessment_question
            ),

            cognitive_result=(
                cognitive_result
            ),
        )


    # ========================================================
    # PROCESS TARGETED REASSESSMENT
    # ========================================================

    def process_reassessment(
        self,
        student: StudentCognitiveModel,
        student_answer: StudentAnswer,
        misconception_description: str,
    ) -> AdaptiveReassessmentResult:
        """
        Process the student's answer to the targeted
        reassessment and automatically replan the next
        Learning Agent action.

        This completes the adaptive loop.
        """

        # ------------------------------------------------
        # STEP 1: VALIDATE USER
        # ------------------------------------------------

        if (
            student.user_id
            != student_answer.user_id
        ):

            raise ValueError(
                "StudentAnswer user_id does not "
                "match StudentCognitiveModel user_id."
            )


        concept_name = (
            student_answer
            .question
            .concept_name
        )


        # ------------------------------------------------
        # STEP 2: PROCESS REASSESSMENT
        # ------------------------------------------------
        #
        # ReassessmentProcessor:
        #
        # - evaluates answer
        # - updates mastery
        # - updates confidence
        # - updates misconception evidence
        # - stores LearningEvidence
        # ------------------------------------------------

        reassessment_result = (
            self.reassessment_processor
            .process(
                student=student,

                student_answer=student_answer,

                misconception_description=(
                    misconception_description
                ),

                source_agent="learning",
            )
        )


        # ------------------------------------------------
        # STEP 3: READ UPDATED CONCEPT STATE
        # ------------------------------------------------

        concept = (
            student.get_concept(
                concept_name
            )
        )


        # ------------------------------------------------
        # STEP 4: CHECK SHARED CROSS-AGENT CONFLICT STATE
        # ------------------------------------------------

        has_active_conflict = (
            self.cognitive_engine
            .has_conflict(
                user_id=student.user_id,

                concept_name=concept_name,
            )
        )


        # ------------------------------------------------
        # STEP 5: LEARNING AGENT REPLANS
        # ------------------------------------------------

        next_action = (
            self.learning_agent
            .choose_action(
                student=student,

                concept_name=concept_name,

                has_conflict=(
                    has_active_conflict
                ),
            )
        )


        # ------------------------------------------------
        # STEP 6: RETURN COMPLETE RESULT
        # ------------------------------------------------

        return AdaptiveReassessmentResult(
            reassessment_result=(
                reassessment_result
            ),

            next_action=(
                next_action
            ),

            has_active_conflict=(
                has_active_conflict
            ),

            mastery=(
                concept.mastery
            ),

            confidence=(
                concept.confidence
            ),

            attempts=(
                concept.attempts
            ),
        )


    # ========================================================
    # GET NEXT ACTION
    # ========================================================

    def get_next_action(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> LearningAction:
        """
        Ask the Learning Agent for the next action using
        the student's CURRENT shared cognitive state.

        This can also be called independently by the
        application after any cognitive update.
        """

        has_active_conflict = (
            self.cognitive_engine
            .has_conflict(
                user_id=student.user_id,

                concept_name=concept_name,
            )
        )


        return (
            self.learning_agent
            .choose_action(
                student=student,

                concept_name=concept_name,

                has_conflict=(
                    has_active_conflict
                ),
            )
        )


    # ========================================================
    # DIFFICULTY CONVERSION
    # ========================================================

    def _difficulty_to_float(
        self,
        difficulty: str,
    ) -> float:
        """
        Convert human-readable difficulty into the
        numerical difficulty used by LearningEvidence.

        These values are engineering heuristics and
        should later be calibrated experimentally.
        """

        difficulty = (
            difficulty
            .strip()
            .lower()
        )


        mapping = {
            "easy": 0.3,
            "medium": 0.6,
            "hard": 0.9,
        }


        return mapping.get(
            difficulty,
            0.5,
        )