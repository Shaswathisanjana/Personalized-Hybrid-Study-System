from dataclasses import dataclass, field


# ==========================================================
# CODING TASK
# ==========================================================

@dataclass
class CodingTask:
    """
    A programming task presented to the student.
    """

    concept_name: str
    title: str
    description: str
    difficulty: str

    starter_code: str = ""
    expected_behavior: str = ""

    misconception_targets: list[str] = field(
        default_factory=list
    )

    def __post_init__(self):
        self.concept_name = self.concept_name.strip()
        self.title = self.title.strip()
        self.description = self.description.strip()
        self.difficulty = self.difficulty.strip().lower()

        if not self.concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if not self.title:
            raise ValueError(
                "title cannot be empty."
            )

        if not self.description:
            raise ValueError(
                "description cannot be empty."
            )

        if self.difficulty not in {
            "easy",
            "medium",
            "hard",
        }:
            raise ValueError(
                "difficulty must be easy, medium, or hard."
            )


# ==========================================================
# STUDENT CODE SUBMISSION
# ==========================================================

@dataclass
class CodingSubmission:
    """
    Code submitted by a student for a CodingTask.
    """

    user_id: str
    task: CodingTask
    code: str

    def __post_init__(self):
        self.user_id = self.user_id.strip()

        if not self.user_id:
            raise ValueError(
                "user_id cannot be empty."
            )

        if not isinstance(
            self.task,
            CodingTask,
        ):
            raise TypeError(
                "task must be a CodingTask."
            )


# ==========================================================
# TEST CASE RESULT
# ==========================================================

@dataclass
class CodingTestResult:
    """
    Result of one test case executed against
    the student's code.
    """

    test_name: str
    passed: bool

    expected_output: str = ""
    actual_output: str = ""
    error: str = ""


# ==========================================================
# CODING EVALUATION
# ==========================================================

@dataclass
class CodingEvaluation:
    """
    Overall evaluation of a coding submission.

    performance:
        Cognitive performance evidence in [0, 1].

    confidence:
        Confidence in the evidence produced by the
        Coding Agent, NOT student confidence.
    """

    is_correct: bool
    performance: float
    confidence: float

    feedback: str

    test_results: list[CodingTestResult] = field(
        default_factory=list
    )

    detected_misconceptions: list[str] = field(
        default_factory=list
    )

    def __post_init__(self):
        if not 0.0 <= self.performance <= 1.0:
            raise ValueError(
                "performance must be between 0 and 1."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1."
            )