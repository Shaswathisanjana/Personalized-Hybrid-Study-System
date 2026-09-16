from app.learning_agent.quiz_models import (
    StudentAnswer,
    EvaluationResult,
)


class AnswerEvaluator:
    """
    Evaluates student answers.

    For questions with a definite correct answer,
    evaluation is deterministic rather than relying
    on an LLM.
    """

    def evaluate(
        self,
        student_answer: StudentAnswer,
    ) -> EvaluationResult:

        expected = (
            student_answer.question.correct_answer
            .strip()
            .lower()
        )

        received = (
            student_answer.answer
            .strip()
            .lower()
        )

        # -------------------------------
        # CORRECT ANSWER
        # -------------------------------

        if received == expected:

            return EvaluationResult(
                is_correct=True,
                performance=1.0,
                feedback="Correct answer.",
                detected_misconceptions=[],
            )

        # -------------------------------
        # INCORRECT ANSWER
        # -------------------------------

        misconceptions = (
            student_answer
            .question
            .misconception_targets
        )

        return EvaluationResult(
            is_correct=False,
            performance=0.0,
            feedback=(
                "The answer is incorrect. "
                f"The expected answer is "
                f"{student_answer.question.correct_answer}."
            ),
            detected_misconceptions=misconceptions,
        )
    