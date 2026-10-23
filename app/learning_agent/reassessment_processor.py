from dataclasses import dataclass

from app.learning_agent.quiz_models import (
    StudentAnswer,
    EvaluationResult,
)

from app.learning_agent.answer_evaluator import (
    AnswerEvaluator,
)

from app.learning_agent.misconception_analyzer import (
    MisconceptionAnalyzer,
)

from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.cognitive.evidence import (
    LearningEvidence,
)

from app.cognitive.cognitive_engine import (
    CognitiveEngine,
)


@dataclass
class ReassessmentResult:
    """
    Result after processing a misconception
    reassessment question.
    """

    evaluation: EvaluationResult

    misconception_detected_again: bool

    hypothesis_confidence: float

    hypothesis_status: str

    supporting_evidence: int

    contradicting_evidence: int

    cognitive_result: dict

    next_action: object | None = None


class ReassessmentProcessor:
    """
    Processes a student's answer to a targeted
    misconception reassessment.

    All cognitive updates are performed through
    CognitiveEngine so that mastery, confidence,
    evidence history, conflicts and misconception
    hypotheses remain in one shared student model.
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine | None = None,
    ):

        self.answer_evaluator = (
            AnswerEvaluator()
        )

        self.misconception_analyzer = (
            MisconceptionAnalyzer()
        )

        self.cognitive_engine = (
            cognitive_engine
            if cognitive_engine is not None
            else CognitiveEngine()
        )


    # ==================================================
    # PROCESS REASSESSMENT
    # ==================================================

    def process(
        self,
        student: StudentCognitiveModel,
        student_answer: StudentAnswer,
        misconception_description: str,
        source_agent: str = "learning",
    ) -> ReassessmentResult:
        """
        Process one targeted reassessment.

        Correct answer:
            1. Add positive mastery evidence.
            2. Add one contradiction against the
               existing misconception hypothesis.

        Incorrect answer:
            1. Analyze whether the SAME misconception
               occurred again.
            2. Add negative mastery evidence.
            3. If the same misconception is detected,
               CognitiveEngine adds one support event.

        Important:
        We never directly update MisconceptionTracker
        from this class.
        """

        # ------------------------------------------------
        # STEP 1: VALIDATE USER
        # ------------------------------------------------

        if student.user_id != student_answer.user_id:

            raise ValueError(
                "StudentAnswer user_id does not "
                "match StudentCognitiveModel user_id."
            )


        question = student_answer.question

        concept_name = question.concept_name


        # ------------------------------------------------
        # STEP 2: GET EXISTING SHARED HYPOTHESIS
        # ------------------------------------------------

        hypothesis = (
            self.cognitive_engine
            .get_misconception_hypothesis(
                student=student,
                concept_name=concept_name,
                misconception=misconception_description,
            )
        )


        if hypothesis is None:

            raise ValueError(
                "The misconception hypothesis does "
                "not exist in the student's shared "
                "cognitive model."
            )


        # ------------------------------------------------
        # STEP 3: EVALUATE STUDENT ANSWER
        # ------------------------------------------------

        evaluation = (
            self.answer_evaluator.evaluate(
                student_answer
            )
        )


        # ==================================================
        # CORRECT REASSESSMENT
        # ==================================================

        if evaluation.is_correct:

            # ----------------------------------------------
            # Correct answer contributes positive evidence
            # toward concept mastery.
            # ----------------------------------------------

            evidence = LearningEvidence(
                user_id=student.user_id,

                concept_name=concept_name,

                source_agent=source_agent,

                evidence_type=(
                    "misconception_reassessment"
                ),

                performance=1.0,

                difficulty=(
                    self._difficulty_to_float(
                        question.difficulty
                    )
                ),

                reliability=0.8,

                detected_misconceptions=[],
            )


            # ----------------------------------------------
            # Update mastery/confidence/evidence history.
            # ----------------------------------------------

            cognitive_result = (
                self.cognitive_engine
                .process_evidence(
                    student=student,
                    evidence=evidence,
                )
            )


            # ----------------------------------------------
            # Correct performance on a question targeted
            # at this misconception is evidence AGAINST
            # the misconception hypothesis.
            #
            # Record exactly ONE contradiction.
            # ----------------------------------------------

            hypothesis = (
                self.cognitive_engine
                .record_misconception_contradiction(
                    student=student,
                    concept_name=concept_name,
                    misconception=(
                        misconception_description
                    ),
                    source_agent=source_agent,
                )
            )


            misconception_detected_again = False


        # ==================================================
        # INCORRECT REASSESSMENT
        # ==================================================

        else:

            # ----------------------------------------------
            # Wrong does NOT automatically mean the same
            # misconception occurred again.
            #
            # Ask the semantic analyzer.
            # ----------------------------------------------

            detected = (
                self.misconception_analyzer
                .analyze(
                    student_answer
                )
            )


            misconception_detected_again = (
                misconception_description
                in detected
            )


            # ----------------------------------------------
            # Only include the misconception in evidence
            # when the analyzer supports the SAME
            # hypothesis.
            #
            # CognitiveEngine will record support exactly
            # once when it processes this evidence.
            # ----------------------------------------------

            if misconception_detected_again:

                detected_for_evidence = [
                    misconception_description
                ]

            else:

                detected_for_evidence = []


            # ----------------------------------------------
            # Incorrect reassessment contributes negative
            # performance evidence to mastery.
            # ----------------------------------------------

            evidence = LearningEvidence(
                user_id=student.user_id,

                concept_name=concept_name,

                source_agent=source_agent,

                evidence_type=(
                    "misconception_reassessment"
                ),

                performance=0.0,

                difficulty=(
                    self._difficulty_to_float(
                        question.difficulty
                    )
                ),

                reliability=0.8,

                detected_misconceptions=(
                    detected_for_evidence
                ),
            )


            # ----------------------------------------------
            # Update the shared cognitive model.
            #
            # If detected_for_evidence contains the
            # misconception, CognitiveEngine also adds
            # one support event to the hypothesis.
            # ----------------------------------------------

            cognitive_result = (
                self.cognitive_engine
                .process_evidence(
                    student=student,
                    evidence=evidence,
                )
            )


            # ----------------------------------------------
            # Retrieve updated shared hypothesis.
            # ----------------------------------------------

            hypothesis = (
                self.cognitive_engine
                .get_misconception_hypothesis(
                    student=student,
                    concept_name=concept_name,
                    misconception=(
                        misconception_description
                    ),
                )
            )


        # ==================================================
        # RETURN RESULT
        # ==================================================

        return ReassessmentResult(
            evaluation=evaluation,

            misconception_detected_again=(
                misconception_detected_again
            ),

            hypothesis_confidence=round(
                hypothesis.confidence,
                3,
            ),

            hypothesis_status=(
                hypothesis.status
            ),

            supporting_evidence=(
                hypothesis.supporting_evidence
            ),

            contradicting_evidence=(
                hypothesis.contradicting_evidence
            ),

            cognitive_result=cognitive_result,

            next_action=None,
        )


    # ==================================================
    # DIFFICULTY CONVERSION
    # ==================================================

    def _difficulty_to_float(
        self,
        difficulty: str,
    ) -> float:
        """
        Convert text difficulty into the numerical
        difficulty used by LearningEvidence.

        These values are engineering heuristics for
        the current prototype and will later be
        calibrated/evaluated.
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