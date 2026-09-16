from dataclasses import dataclass, field

from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
)


@dataclass
class RemediationContext:
    """
    Stores the evidence that led to a remediation.

    This prevents the teaching system from relying
    only on an LLM-generated misconception label.
    """

    concept_name: str

    original_question: str

    correct_answer: str

    student_answer: str

    detected_misconceptions: list[str] = field(
        default_factory=list
    )

    explanation: str = ""

    def build_grounding_text(self) -> str:
        """
        Creates grounded context for the teaching
        content generator.
        """

        misconception_text = (
            "; ".join(self.detected_misconceptions)
            if self.detected_misconceptions
            else "No specific misconception identified."
        )

        return (
            f"Original question:\n"
            f"{self.original_question}\n\n"

            f"Correct answer:\n"
            f"{self.correct_answer}\n\n"

            f"Student answer:\n"
            f"{self.student_answer}\n\n"

            f"Detected misconception hypothesis:\n"
            f"{misconception_text}\n\n"

            f"Original question explanation:\n"
            f"{self.explanation}"
        )


def create_remediation_context(
    student_answer: StudentAnswer,
    detected_misconceptions: list[str],
) -> RemediationContext:
    """
    Creates remediation context directly from
    the actual quiz interaction.
    """

    question: QuizQuestion = (
        student_answer.question
    )

    return RemediationContext(
        concept_name=question.concept_name,

        original_question=question.question,

        correct_answer=question.correct_answer,

        student_answer=student_answer.answer,

        detected_misconceptions=(
            detected_misconceptions.copy()
        ),

        explanation=question.explanation,
    )
