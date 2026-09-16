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

from app.cognitive.misconception_tracker import (
    MisconceptionHypothesis,
    MisconceptionTracker,
)


@dataclass
class ReassessmentResult:
    evaluation: EvaluationResult

    misconception_detected_again: bool

    hypothesis_confidence: float

    hypothesis_status: str

    supporting_evidence: int

    contradicting_evidence: int


class ReassessmentProcessor:
    """
    Processes a student's answer to a question
    designed to reassess a misconception hypothesis.
    """

    def __init__(self):
        self.answer_evaluator = AnswerEvaluator()

        self.misconception_analyzer = (
            MisconceptionAnalyzer()
        )

        self.tracker = MisconceptionTracker()


    def process(
        self,
        student_answer: StudentAnswer,
        hypothesis: MisconceptionHypothesis,
        source_agent: str = "learning",
    ) -> ReassessmentResult:

        # ------------------------------------------
        # STEP 1: Evaluate the actual answer
        # ------------------------------------------

        evaluation = (
            self.answer_evaluator.evaluate(
                student_answer
            )
        )


        # ------------------------------------------
        # STEP 2: Correct answer
        #
        # A correct answer is evidence AGAINST
        # the misconception hypothesis.
        # ------------------------------------------

        if evaluation.is_correct:

            self.tracker.add_contradiction(
                hypothesis=hypothesis,
                source_agent=source_agent,
            )

            misconception_detected_again = False


        # ------------------------------------------
        # STEP 3: Incorrect answer
        #
        # Wrong does NOT automatically mean the
        # misconception occurred again.
        # Ask the semantic analyzer.
        # ------------------------------------------

        else:

            detected = (
                self.misconception_analyzer.analyze(
                    student_answer
                )
            )

            misconception_detected_again = (
                hypothesis.description in detected
            )


            # --------------------------------------
            # Only strengthen the hypothesis if
            # the SAME misconception is supported.
            # --------------------------------------

            if misconception_detected_again:

                self.tracker.add_support(
                    hypothesis=hypothesis,
                    source_agent=source_agent,
                )


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
        )