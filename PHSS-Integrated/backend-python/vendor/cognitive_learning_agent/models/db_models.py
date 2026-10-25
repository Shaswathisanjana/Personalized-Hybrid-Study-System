"""SQLAlchemy ORM models for Cognitive Memory persistence."""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DBLearner(Base):
    __tablename__ = "learners"

    user_id = Column(String(128), primary_key=True)
    name = Column(String(256), nullable=False, default="Learner")
    learning_goal = Column(Text, nullable=False)
    current_level = Column(String(64), nullable=False, default="beginner")
    preferred_format = Column(String(64), nullable=False, default="any")
    target_outcome = Column(Text, nullable=False)
    preferred_language = Column(String(64), nullable=True, default="Python")
    recommended_path_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    concept_masteries = relationship("DBConceptMastery", back_populates="learner", cascade="all, delete-orphan")
    prerequisites = relationship("DBPrerequisite", back_populates="learner", cascade="all, delete-orphan")
    misconceptions = relationship("DBMisconception", back_populates="learner", cascade="all, delete-orphan")
    evidence_items = relationship("DBEvidenceItem", back_populates="learner", cascade="all, delete-orphan")
    history_items = relationship("DBLearningHistory", back_populates="learner", cascade="all, delete-orphan")
    quiz_attempts = relationship("DBQuizAttempt", back_populates="learner", cascade="all, delete-orphan")


class DBConceptMastery(Base):
    __tablename__ = "concept_mastery"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(128), ForeignKey("learners.user_id"), nullable=False)
    concept_name = Column(String(256), nullable=False)
    mastery_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.1)
    status = Column(String(64), nullable=False, default="NOT_STARTED")
    evidence_count = Column(Integer, nullable=False, default=0)
    last_evaluated_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("learner_id", "concept_name", name="uix_learner_concept"),
    )

    learner = relationship("DBLearner", back_populates="concept_masteries")


class DBPrerequisite(Base):
    __tablename__ = "prerequisites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(128), ForeignKey("learners.user_id"), nullable=False)
    concept_name = Column(String(256), nullable=False)
    prerequisite_name = Column(String(256), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)

    __table_args__ = (
        UniqueConstraint("learner_id", "concept_name", "prerequisite_name", name="uix_concept_prereq"),
    )

    learner = relationship("DBLearner", back_populates="prerequisites")


class DBMisconception(Base):
    __tablename__ = "misconceptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(128), ForeignKey("learners.user_id"), nullable=False)
    concept_name = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    evidence_observation = Column(Text, nullable=False)
    status = Column(String(64), nullable=False, default="ACTIVE")
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    remediation_notes = Column(Text, nullable=True)

    learner = relationship("DBLearner", back_populates="misconceptions")


class DBEvidenceItem(Base):
    __tablename__ = "evidence_store"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(128), ForeignKey("learners.user_id"), nullable=False)
    concept_name = Column(String(256), nullable=False)
    evidence_type = Column(String(64), nullable=False)
    score = Column(Float, nullable=True)
    resource_url = Column(String(1024), nullable=True)
    observation = Column(Text, nullable=False)
    user_feedback_rating = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    learner = relationship("DBLearner", back_populates="evidence_items")


class DBLearningHistory(Base):
    __tablename__ = "learning_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(128), ForeignKey("learners.user_id"), nullable=False)
    resource_url = Column(String(1024), nullable=False)
    title = Column(String(512), nullable=False)
    format = Column(String(64), nullable=False, default="documentation")
    completed = Column(Boolean, nullable=False, default=True)
    perceived_difficulty = Column(String(64), nullable=True)
    usefulness_rating = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    learner = relationship("DBLearner", back_populates="history_items")


class DBLearningJourney(Base):
    __tablename__ = "learning_journeys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(128), ForeignKey("learners.user_id"), nullable=False)
    topic_title = Column(String(256), nullable=False)
    learning_goal = Column(Text, nullable=False)
    target_outcome = Column(Text, nullable=False)
    path_json = Column(Text, nullable=True)
    total_topics = Column(Integer, default=0)
    completed_topics = Column(Integer, default=0)
    mastery_percentage = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    learner = relationship("DBLearner")


class DBQuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    learner_id = Column(String(128), ForeignKey("learners.user_id"), nullable=False)
    concept_name = Column(String(256), nullable=False)
    subtopic_name = Column(String(256), nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)
    score = Column(Float, nullable=False, default=0.0)
    passed = Column(Boolean, nullable=False, default=False)
    total_questions = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    quiz_type = Column(String(64), nullable=False, default="initial")
    questions_data = Column(Text, nullable=True)  # JSON serialized question responses
    weak_areas = Column(Text, nullable=True)  # JSON list
    misconceptions = Column(Text, nullable=True)  # JSON list
    recommended_resources = Column(Text, nullable=True)  # JSON list
    remediation_efficacy = Column(Text, nullable=True)  # JSON dict
    next_action = Column(String(64), nullable=True)  # PROCEED, REVISE, REVISIT_PREREQUISITE
    next_action_reason = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    learner = relationship("DBLearner", back_populates="quiz_attempts")
