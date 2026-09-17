from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResearchRequest:
    """
    Represents a student's research request.
    """

    user_id: str
    topic: str
    question: str

    def __post_init__(self):
        self.user_id = self.user_id.strip()
        self.topic = self.topic.strip()
        self.question = self.question.strip()

        if not self.user_id:
            raise ValueError("user_id cannot be empty")

        if not self.topic:
            raise ValueError("topic cannot be empty")

        if not self.question:
            raise ValueError("question cannot be empty")


@dataclass
class ResearchPaper:
    """
    Standard representation of a research paper retrieved
    by the Research Agent.
    """

    title: str
    authors: list[str]
    abstract: str
    url: str

    year: Optional[int] = None
    source: str = ""
    paper_id: str = ""

    def __post_init__(self):
        self.title = self.title.strip()
        self.abstract = self.abstract.strip()
        self.url = self.url.strip()
        self.source = self.source.strip().lower()
        self.paper_id = self.paper_id.strip()

        if not self.title:
            raise ValueError("Research paper title cannot be empty")


@dataclass
class ResearchEvidenceItem:
    """
    A grounded piece of information extracted from
    a research paper.

    This is NOT cognitive evidence about the student.

    It represents research evidence from a paper.
    """

    claim: str
    paper_title: str
    paper_url: str
    relevance: float

    def __post_init__(self):
        self.claim = self.claim.strip()
        self.paper_title = self.paper_title.strip()
        self.paper_url = self.paper_url.strip()

        if not self.claim:
            raise ValueError("Research evidence claim cannot be empty")

        if not 0.0 <= self.relevance <= 1.0:
            raise ValueError("relevance must be between 0 and 1")


@dataclass
class ResearchSynthesis:
    """
    Final grounded research response produced from
    retrieved research evidence.
    """

    topic: str
    question: str
    answer: str

    evidence: list[ResearchEvidenceItem] = field(
        default_factory=list
    )

    papers_used: list[ResearchPaper] = field(
        default_factory=list
    )


@dataclass
class ResearchComprehensionQuestion:
    """
    Assessment generated after a research interaction.

    It tests whether the student understood the concept,
    rather than whether the Research Agent generated a
    good answer.
    """

    concept_name: str
    question: str
    correct_answer: str
    explanation: str

    difficulty: str = "medium"

    misconception_targets: list[str] = field(
        default_factory=list
    )


@dataclass
class ResearchStudentAnswer:
    """
    Student response to a research comprehension question.
    """

    user_id: str
    question: ResearchComprehensionQuestion
    answer: str


@dataclass
class ResearchComprehensionEvaluation:
    """
    Result of evaluating the student's understanding
    after interacting with research material.
    """

    is_correct: bool
    performance: float
    confidence: float
    feedback: str

    detected_misconceptions: list[str] = field(
        default_factory=list
    )