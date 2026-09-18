from dataclasses import dataclass, field
from datetime import datetime

from app.learning_agent.quiz_models import (
    QuizQuestion,
    EvaluationResult,
)
from app.learning_agent.gemini_quiz_generator import (
    PreviousQuestion,
)


@dataclass
class PracticeAttempt:
    """
    Represents one completed question inside an
    adaptive practice session.

    It stores:
    - the question shown to the student
    - the student's answer
    - the evaluation produced by the system

    This becomes the practice history used when
    generating later questions.
    """

    question: QuizQuestion
    student_answer: str
    evaluation: EvaluationResult

    completed_at: datetime = field(
        default_factory=datetime.now
    )


@dataclass
class PracticeSession:
    """
    Represents one adaptive practice session for
    a single student and concept.

    The session does NOT calculate mastery and does
    NOT make CACM decisions.

    It only stores the history required by the
    Learning Agent while the adaptive session runs.
    """

    user_id: str
    concept_name: str

    learning_context: str | None = None

    max_questions: int = 3

    attempts: list[PracticeAttempt] = field(
        default_factory=list
    )

    current_question: QuizQuestion | None = None

    started_at: datetime = field(
        default_factory=datetime.now
    )

    completed_at: datetime | None = None

    def __post_init__(self):
        self.user_id = self.user_id.strip()
        self.concept_name = self.concept_name.strip()

        if not self.user_id:
            raise ValueError(
                "user_id cannot be empty."
            )

        if not self.concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if self.learning_context is not None:
            self.learning_context = (
                self.learning_context.strip()
            )

            if not self.learning_context:
                self.learning_context = None

        if self.max_questions < 1:
            raise ValueError(
                "max_questions must be at least 1."
            )

    # =====================================================
    # SESSION STATE
    # =====================================================

    @property
    def questions_completed(self) -> int:
        """
        Number of questions already answered.
        """

        return len(self.attempts)

    @property
    def questions_remaining(self) -> int:
        """
        Number of questions remaining in the session.
        """

        return max(
            0,
            self.max_questions
            - self.questions_completed,
        )

    @property
    def is_complete(self) -> bool:
        """
        Whether the planned practice session has ended.
        """

        return (
            self.questions_completed
            >= self.max_questions
        )

    # =====================================================
    # QUESTION MANAGEMENT
    # =====================================================

    def set_current_question(
        self,
        question: QuizQuestion,
    ) -> None:
        """
        Store the question currently being shown
        to the student.
        """

        if self.is_complete:
            raise ValueError(
                "Practice session is already complete."
            )

        self.current_question = question

    def record_attempt(
        self,
        student_answer: str,
        evaluation: EvaluationResult,
    ) -> PracticeAttempt:
        """
        Record the student's response to the current
        question.

        CACM updating happens elsewhere. This class only
        records the interaction history.
        """

        if self.current_question is None:
            raise ValueError(
                "There is no active practice question."
            )

        if self.is_complete:
            raise ValueError(
                "Practice session is already complete."
            )

        answer = student_answer.strip()

        if not answer:
            raise ValueError(
                "student_answer cannot be empty."
            )

        attempt = PracticeAttempt(
            question=self.current_question,
            student_answer=answer,
            evaluation=evaluation,
        )

        self.attempts.append(attempt)

        self.current_question = None

        if self.is_complete:
            self.completed_at = datetime.now()

        return attempt

    # =====================================================
    # GENERATOR HISTORY
    # =====================================================

    def get_question_history(
        self,
    ) -> list[PreviousQuestion]:
        """
        Convert completed attempts into the compact
        history expected by GeminiQuizGenerator.

        This prevents unnecessary repeated questions.
        """

        history = []

        for attempt in self.attempts:
            history.append(
                PreviousQuestion(
                    question=(
                        attempt.question.question
                    ),
                    performance=(
                        attempt.evaluation.performance
                    ),
                    misconception_targets=(
                        attempt.evaluation
                        .detected_misconceptions
                        or attempt.question
                        .misconception_targets
                    ),
                )
            )

        return history

    # =====================================================
    # MISCONCEPTION HISTORY
    # =====================================================

    def get_unresolved_misconception_candidates(
        self,
    ) -> list[str]:
        """
        Return misconception hypotheses observed during
        unsuccessful answers in this practice session.

        These are only CANDIDATES.

        The Learning Agent/CACM decides whether they should
        actually influence the next pedagogical action.
        """

        candidates = []

        for attempt in self.attempts:
            if attempt.evaluation.performance >= 1.0:
                continue

            for misconception in (
                attempt.evaluation
                .detected_misconceptions
            ):
                cleaned = misconception.strip()

                if (
                    cleaned
                    and cleaned not in candidates
                ):
                    candidates.append(cleaned)

        return candidates

    # =====================================================
    # PERFORMANCE SUMMARY
    # =====================================================

    def average_performance(
        self,
    ) -> float:
        """
        Mean performance across completed questions.

        This is a session statistic only.

        It must NOT replace CACM mastery.
        """

        if not self.attempts:
            return 0.0

        total = sum(
            attempt.evaluation.performance
            for attempt in self.attempts
        )

        return total / len(self.attempts)