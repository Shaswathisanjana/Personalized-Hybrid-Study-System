from dataclasses import dataclass, field


@dataclass
class QuizQuestion:
    """
    Structured representation of a question generated
    by the Learning Agent.
    """

    concept_name: str
    difficulty: str

    question: str

    question_type: str = "short_answer"

    correct_answer: str = ""

    explanation: str = ""

    misconception_targets: list[str] = field(
        default_factory=list
    )


@dataclass
class StudentAnswer:
    """
    Stores the student's response to a quiz question.
    """

    user_id: str

    question: QuizQuestion

    answer: str


@dataclass
class EvaluationResult:
    """
    Result produced after evaluating the student's answer.
    """

    is_correct: bool

    performance: float

    feedback: str

    detected_misconceptions: list[str] = field(
        default_factory=list
    )