from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine

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


@dataclass
class RemediationLoopResult:
    """
    Result produced after processing an incorrect
    student answer.
    """

    evaluation: EvaluationResult

    detected_misconceptions: list[str]

    remediation_context: RemediationContext | None

    remediation_content: object | None

    reassessment_question: QuizQuestion | None

    cognitive_result: dict | None


class RemediationLoop:
    """
    Coordinates the misconception-remediation cycle.

    Flow:

    Student answer
        ↓
    Answer evaluation
        ↓
    Misconception analysis
        ↓
    Cognitive evidence
        ↓
    Shared cognitive model
        ↓
    Grounded remediation
        ↓
    Reassessment question
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine | None = None,
    ):

        self.cognitive_engine = (
            cognitive_engine
            if cognitive_engine is not None
            else CognitiveEngine()
        )

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


    # ==================================================
    # PROCESS ORIGINAL ANSWER
    # ==================================================

    def process_answer(
        self,
        student: StudentCognitiveModel,
        student_answer: StudentAnswer,
    ) -> RemediationLoopResult:
        """
        Process the student's answer to the original
        quiz question.

        If correct:
            no remediation is required.

        If incorrect:
            1. analyze misconception
            2. update cognitive model
            3. generate grounded remediation
            4. generate reassessment
        """

        # ------------------------------------------------
        # STEP 1: CHECK USER
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


        # ------------------------------------------------
        # STEP 3: CORRECT ANSWER
        # ------------------------------------------------
        #
        # No misconception remediation is necessary.
        # ------------------------------------------------

        if evaluation.is_correct:

            evidence = LearningEvidence(
                user_id=student.user_id,

                concept_name=(
                    student_answer
                    .question
                    .concept_name
                ),

                source_agent="learning",

                evidence_type="quiz",

                performance=1.0,

                difficulty=self._difficulty_to_float(
                    student_answer
                    .question
                    .difficulty
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


        # ------------------------------------------------
        # STEP 4: ANALYZE WRONG ANSWER
        # ------------------------------------------------

        detected_misconceptions = (
            self.misconception_analyzer
            .analyze(
                student_answer
            )
        )


        # ------------------------------------------------
        # STEP 5: CREATE LEARNING EVIDENCE
        # ------------------------------------------------

        evidence = LearningEvidence(
            user_id=student.user_id,

            concept_name=(
                student_answer
                .question
                .concept_name
            ),

            source_agent="learning",

            evidence_type="quiz",

            performance=0.0,

            difficulty=self._difficulty_to_float(
                student_answer
                .question
                .difficulty
            ),

            reliability=0.7,

            detected_misconceptions=(
                detected_misconceptions
            ),
        )


        # ------------------------------------------------
        # STEP 6: UPDATE SHARED COGNITIVE MODEL
        # ------------------------------------------------

        cognitive_result = (
            self.cognitive_engine
            .process_evidence(
                student=student,
                evidence=evidence,
            )
        )


        # ------------------------------------------------
        # STEP 7: NO SPECIFIC MISCONCEPTION FOUND
        # ------------------------------------------------
        #
        # A wrong answer does not automatically mean
        # that we know WHY it was wrong.
        #
        # If Gemini cannot identify one of the allowed
        # misconception targets, we stop targeted
        # remediation here.
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
        # STEP 8: BUILD GROUNDED REMEDIATION CONTEXT
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
        # STEP 9: GENERATE GROUNDED REMEDIATION
        # ------------------------------------------------

        remediation_content = (
            self.remediation_generator.generate(
                student=student,

                context=remediation_context,
            )
        )


        # ------------------------------------------------
        # STEP 10: GENERATE REASSESSMENT
        # ------------------------------------------------
        #
        # For now we target the first detected
        # misconception.
        #
        # Later we can prioritize multiple
        # misconceptions by confidence.
        # ------------------------------------------------

        target_misconception = (
            detected_misconceptions[0]
        )


        reassessment_question = (
            self.reassessment_generator.generate(
                concept_name=(
                    student_answer
                    .question
                    .concept_name
                ),

                misconception=(
                    target_misconception
                ),

                previous_question=(
                    student_answer
                    .question
                    .question
                ),
            )
        )


        # ------------------------------------------------
        # STEP 11: RETURN EVERYTHING
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


    # ==================================================
    # DIFFICULTY CONVERSION
    # ==================================================

    def _difficulty_to_float(
        self,
        difficulty: str,
    ) -> float:
        """
        Convert the human-readable quiz difficulty
        into the numerical value used by the
        cognitive evidence model.

        These mappings are currently engineering
        heuristics and will later be calibrated.
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