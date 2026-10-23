from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LearningResource:
    """
    Represents one real external learning resource.

    A resource may be:
    - a video
    - an article/tutorial
    - documentation
    - another educational webpage

    Retrieval and ranking are deliberately separated.
    APIs retrieve candidate resources, while our
    recommender decides which resources best match
    the student's current learning needs.
    """

    title: str
    url: str
    resource_type: str

    description: str = ""
    source: str = ""

    # Difficulty assigned/estimated for personalization.
    difficulty: str = "medium"

    # Optional metadata supplied by the retrieval source.
    duration_minutes: Optional[float] = None
    published_year: Optional[int] = None

    # Useful later when the retrieval source provides
    # popularity/quality information.
    view_count: Optional[int] = None

    # Terms describing the educational content.
    topics: list[str] = field(
        default_factory=list
    )

    def __post_init__(self):

        self.title = self.title.strip()
        self.url = self.url.strip()
        self.resource_type = (
            self.resource_type.strip().lower()
        )
        self.difficulty = (
            self.difficulty.strip().lower()
        )

        if not self.title:
            raise ValueError(
                "Resource title cannot be empty."
            )

        if not self.url:
            raise ValueError(
                "Resource URL cannot be empty."
            )

        valid_types = {
            "video",
            "article",
            "tutorial",
            "documentation",
            "webpage",
        }

        if self.resource_type not in valid_types:
            raise ValueError(
                f"Unsupported resource type: "
                f"{self.resource_type}"
            )

        valid_difficulties = {
            "easy",
            "medium",
            "hard",
        }

        if self.difficulty not in valid_difficulties:
            raise ValueError(
                f"Unsupported difficulty: "
                f"{self.difficulty}"
            )


@dataclass
class RankedLearningResource:
    """
    Learning resource after personalization/ranking.

    The separate component scores are intentionally
    preserved so that the recommendation is
    explainable during evaluation and demonstrations.
    """

    resource: LearningResource

    relevance_score: float
    difficulty_match_score: float
    quality_score: float

    final_score: float

    reason: str = ""

    def __post_init__(self):

        score_fields = {
            "relevance_score": self.relevance_score,
            "difficulty_match_score":
                self.difficulty_match_score,
            "quality_score": self.quality_score,
            "final_score": self.final_score,
        }

        for name, value in score_fields.items():

            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between "
                    f"0.0 and 1.0."
                )


@dataclass
class ResourceRecommendation:
    """
    Final recommendation returned to the Learning Agent.
    """

    concept_name: str
    student_level: str

    resources: list[RankedLearningResource] = field(
        default_factory=list
    )