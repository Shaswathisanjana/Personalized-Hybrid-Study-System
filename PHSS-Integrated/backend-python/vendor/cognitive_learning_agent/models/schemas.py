"""Pydantic schemas for Cognitive Learning Agent."""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LearningFormat(str, Enum):
    ANY = "any"
    VIDEO = "video"
    DOCUMENTATION = "documentation"
    INTERACTIVE = "interactive"
    PRACTICE = "practice"
    VISUALIZATION = "visualization"


class ConceptStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PROFICIENT = "PROFICIENT"
    MASTERED = "MASTERED"


class EvidenceType(str, Enum):
    COMPLETION = "COMPLETION"
    QUIZ = "QUIZ"
    SELF_RATING = "SELF_RATING"
    PRACTICE = "PRACTICE"
    CONFUSION_REPORT = "CONFUSION_REPORT"


class MisconceptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RECTIFIED = "RECTIFIED"


class ConflictSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class LearnerProfileCreate(BaseModel):
    user_id: str = Field(..., description="Unique identifier for learner")
    name: str = Field(default="Learner", description="Learner's name")
    learning_goal: str = Field(..., description="What the learner wants to learn")
    current_level: DifficultyLevel = Field(default=DifficultyLevel.BEGINNER)
    preferred_format: LearningFormat = Field(default=LearningFormat.ANY)
    target_outcome: str = Field(..., description="Specific target project or capability outcome")
    preferred_language: Optional[str] = Field(default="Python", description="Programming language or context")


class LearnerProfile(LearnerProfileCreate):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ConceptMasteryItem(BaseModel):
    concept_name: str
    mastery_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_score: float = Field(default=0.1, ge=0.0, le=1.0)
    status: ConceptStatus = Field(default=ConceptStatus.NOT_STARTED)
    evidence_count: int = Field(default=0)
    last_evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None


class PrerequisiteRelation(BaseModel):
    concept_name: str
    prerequisite_name: str
    weight: float = Field(default=1.0, ge=0.1, le=1.0)


class MisconceptionItem(BaseModel):
    id: Optional[int] = None
    learner_id: str
    concept_name: str
    description: str
    evidence_observation: str
    status: MisconceptionStatus = MisconceptionStatus.ACTIVE
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    remediation_notes: Optional[str] = None


class EvidenceItem(BaseModel):
    id: Optional[int] = None
    learner_id: str
    concept_name: str
    evidence_type: EvidenceType
    score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    resource_url: Optional[str] = None
    observation: str
    user_feedback_rating: Optional[int] = Field(default=None, ge=1, le=5)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LearningResource(BaseModel):
    url: str
    title: str
    snippet: str
    domain: str
    format: LearningFormat = LearningFormat.DOCUMENTATION
    difficulty: DifficultyLevel = DifficultyLevel.BEGINNER
    target_concept: str
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_valid: bool = True
    status_code: Optional[int] = 200
    estimated_minutes: int = Field(default=15, ge=1)
    word_count: Optional[int] = None
    prerequisite_concept: Optional[str] = None


class LearningPath(BaseModel):
    learner_id: str
    goal: str
    target_outcome: str
    resources: List[LearningResource] = Field(default_factory=list)
    ordered_concepts: List[str] = Field(default_factory=list)
    rationale: str = ""
    estimated_total_minutes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AssessmentFeedback(BaseModel):
    learner_id: str
    concept_name: str
    resource_url: Optional[str] = None
    completed: bool = True
    quiz_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    perceived_difficulty: Optional[str] = Field(
        default="just_right",
        description="'too_easy', 'just_right', or 'too_hard'"
    )
    usefulness_rating: Optional[int] = Field(default=4, ge=1, le=5)
    confusion_reported: bool = False
    notes: Optional[str] = None


class CognitiveConflict(BaseModel):
    concept_name: str
    severity: ConflictSeverity
    description: str
    claimed_mastery: float
    observed_performance: float
    resolution_action: str


class CognitiveStateSnapshot(BaseModel):
    learner: LearnerProfile
    concepts: Dict[str, ConceptMasteryItem] = Field(default_factory=dict)
    prerequisites: List[PrerequisiteRelation] = Field(default_factory=list)
    active_misconceptions: List[MisconceptionItem] = Field(default_factory=list)
    rectified_misconceptions: List[MisconceptionItem] = Field(default_factory=list)
    recent_evidence: List[EvidenceItem] = Field(default_factory=list)
    detected_conflicts: List[CognitiveConflict] = Field(default_factory=list)
    overall_progress: float = 0.0


class ReplanResult(BaseModel):
    replan_triggered: bool
    reasons: List[str]
    actions_taken: List[str]
    updated_learning_path: LearningPath
    conflicts_detected: List[CognitiveConflict] = Field(default_factory=list)
    active_misconceptions: List[MisconceptionItem] = Field(default_factory=list)


class QuestionType(str, Enum):
    MCQ = "mcq"
    DESCRIPTIVE = "descriptive"
    PREDICT_OUTPUT = "predict_output"


class NextLearningAction(str, Enum):
    PROCEED = "PROCEED"
    REVISE = "REVISE"
    REVISIT_PREREQUISITE = "REVISIT_PREREQUISITE"


class QuizQuestion(BaseModel):
    question_id: int
    question_type: QuestionType = QuestionType.MCQ
    question_text: str
    code_snippet: Optional[str] = None  # Code block for Predict Output questions
    options: List[str] = Field(default_factory=list)  # For MCQ and Predict Output
    correct_option_index: int = 0  # For MCQ and Predict Output
    explanation: str
    concept_aspect: str
    distractor_misconceptions: Dict[int, str] = Field(default_factory=dict)
    ideal_answer: Optional[str] = None  # For Descriptive
    rubric_keywords: List[str] = Field(default_factory=list)  # For Descriptive
    is_revision: bool = False  # True if selected as a retention check from previously mastered concepts


class ConceptQuiz(BaseModel):
    concept_name: str
    resource_url: Optional[str] = None
    attempt_number: int = 1
    quiz_type: str = "initial"  # "initial" | "adaptive"
    questions: List[QuizQuestion] = Field(default_factory=list)


class QuizSubmission(BaseModel):
    learner_id: str = ""
    concept_name: str
    resource_url: Optional[str] = None
    attempt_number: Optional[int] = None
    selected_answers: Dict[int, int] = Field(default_factory=dict)  # question_id -> option index (for MCQs / Predict Output)
    answers: Optional[Dict[int, int]] = None  # convenient alias for selected_answers
    descriptive_answers: Dict[int, str] = Field(default_factory=dict)  # question_id -> text response (for Descriptive)

    def model_post_init(self, __context: Any) -> None:
        if self.answers and not self.selected_answers:
            self.selected_answers = self.answers


class QuizAttemptRecord(BaseModel):
    id: Optional[int] = None
    learner_id: str
    concept_name: str
    subtopic_name: Optional[str] = None
    attempt_number: int = 1
    score: float = 0.0
    passed: bool = False
    total_questions: int = 0
    correct_count: int = 0
    quiz_type: str = "initial"
    questions_data: List[Dict[str, Any]] = Field(default_factory=list)
    weak_areas: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    recommended_resources: List[Dict[str, Any]] = Field(default_factory=list)
    remediation_efficacy: Optional[Dict[str, Any]] = None
    next_action: NextLearningAction = NextLearningAction.PROCEED
    next_action_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QuizEvaluationResult(BaseModel):
    concept_name: str
    attempt_number: int = 1
    quiz_type: str = "initial"
    total_questions: int
    correct_count: int
    score: float
    passed: bool
    question_feedback: List[Dict[str, Any]] = Field(default_factory=list)
    weak_areas: List[str] = Field(default_factory=list)
    detected_misconceptions: List[str] = Field(default_factory=list)
    targeted_resources: List[LearningResource] = Field(default_factory=list)
    remediation_efficacy: Optional[Dict[str, Any]] = None
    next_action: NextLearningAction = NextLearningAction.PROCEED
    next_action_reason: str = ""
    prior_mastery: Optional[float] = None
    replan_result: Optional[ReplanResult] = None

    @property
    def misconceptions(self) -> List[str]:
        return self.detected_misconceptions


