from app.learning_agent.quiz_models import (
    StudentAnswer,
    EvaluationResult,
)


class AnswerEvaluator:
    """
    Evaluates objectively gradable student answers.

    Important:
    A wrong answer alone does not prove which
    misconception caused the error.

    Misconceptions will be identified separately
    by the MisconceptionAnalyzer.
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

        # Correct answer
        if received == expected:
            return EvaluationResult(
                is_correct=True,
                performance=1.0,
                feedback="Correct answer.",
                detected_misconceptions=[],
            )

        # Wrong answer
        # Do NOT automatically assign all possible
        # misconception targets.
        return EvaluationResult(
            is_correct=False,
            performance=0.0,
            feedback=(
                "The answer is incorrect. "
                f"The expected answer is "
                f"{student_answer.question.correct_answer}."
            ),
            detected_misconceptions=[],
        )