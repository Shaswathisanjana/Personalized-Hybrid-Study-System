import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc

from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    LearnerProfile,
    ConceptMasteryItem,
    ConceptStatus,
    PrerequisiteRelation,
    MisconceptionItem,
    MisconceptionStatus,
    EvidenceItem,
    EvidenceType,
    CognitiveStateSnapshot,
    LearningPath,
    QuizAttemptRecord,
    NextLearningAction,
)
from cognitive_learning_agent.models.db_models import (
    DBLearner,
    DBConceptMastery,
    DBPrerequisite,
    DBMisconception,
    DBEvidenceItem,
    DBLearningHistory,
    DBLearningJourney,
    DBQuizAttempt,
)


class CognitiveMemoryRepository:
    """Manages persistent storage and querying of student cognitive states."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    # ---------------------------------------------------------
    # Learner Profile
    # ---------------------------------------------------------
    def upsert_learner(self, profile: LearnerProfileCreate) -> LearnerProfile:
        with self.session_factory() as session:
            db_learner = session.query(DBLearner).filter_by(user_id=profile.user_id).first()
            if not db_learner:
                db_learner = DBLearner(
                    user_id=profile.user_id,
                    name=profile.name,
                    learning_goal=profile.learning_goal,
                    current_level=profile.current_level.value,
                    preferred_format=profile.preferred_format.value,
                    target_outcome=profile.target_outcome,
                    preferred_language=profile.preferred_language,
                )
                session.add(db_learner)
            else:
                db_learner.name = profile.name
                db_learner.learning_goal = profile.learning_goal
                db_learner.current_level = profile.current_level.value
                db_learner.preferred_format = profile.preferred_format.value
                db_learner.target_outcome = profile.target_outcome
                db_learner.preferred_language = profile.preferred_language
                db_learner.updated_at = datetime.utcnow()
            session.commit()
            return self._to_learner_profile(db_learner)

    def get_learner(self, user_id: str) -> Optional[LearnerProfile]:
        with self.session_factory() as session:
            db_learner = session.query(DBLearner).filter_by(user_id=user_id).first()
            if not db_learner:
                return None
            return self._to_learner_profile(db_learner)

    def list_learners(self) -> List[LearnerProfile]:
        with self.session_factory() as session:
            db_learners = session.query(DBLearner).all()
            return [self._to_learner_profile(dl) for dl in db_learners]

    def save_learning_path(self, user_id: str, path: LearningPath):
        """Persist serialized LearningPath in database."""
        with self.session_factory() as session:
            db_learner = session.query(DBLearner).filter_by(user_id=user_id).first()
            if db_learner:
                db_learner.recommended_path_json = path.model_dump_json()
                db_learner.updated_at = datetime.utcnow()
                session.commit()

    def get_learning_path(self, user_id: str) -> Optional[LearningPath]:
        """Fetch persisted LearningPath from database."""
        with self.session_factory() as session:
            db_learner = session.query(DBLearner).filter_by(user_id=user_id).first()
            if db_learner and db_learner.recommended_path_json:
                try:
                    import json
                    data = json.loads(db_learner.recommended_path_json)
                    return LearningPath(**data)
                except Exception:
                    pass
            return None

    # ---------------------------------------------------------
    # Concept Mastery
    # ---------------------------------------------------------
    def upsert_concept_mastery(self, user_id: str, concept: ConceptMasteryItem) -> ConceptMasteryItem:
        with self.session_factory() as session:
            db_concept = (
                session.query(DBConceptMastery)
                .filter_by(learner_id=user_id, concept_name=concept.concept_name)
                .first()
            )
            if not db_concept:
                db_concept = DBConceptMastery(
                    learner_id=user_id,
                    concept_name=concept.concept_name,
                    mastery_score=concept.mastery_score,
                    confidence_score=concept.confidence_score,
                    status=concept.status.value,
                    evidence_count=concept.evidence_count,
                    last_evaluated_at=concept.last_evaluated_at,
                    notes=concept.notes,
                )
                session.add(db_concept)
            else:
                db_concept.mastery_score = concept.mastery_score
                db_concept.confidence_score = concept.confidence_score
                db_concept.status = concept.status.value
                db_concept.evidence_count = concept.evidence_count
                db_concept.last_evaluated_at = datetime.utcnow()
                if concept.notes:
                    db_concept.notes = concept.notes
            session.commit()
            return self._to_concept_item(db_concept)

    def get_concept_masteries(self, user_id: str) -> Dict[str, ConceptMasteryItem]:
        with self.session_factory() as session:
            db_items = session.query(DBConceptMastery).filter_by(learner_id=user_id).all()
            return {item.concept_name: self._to_concept_item(item) for item in db_items}

    def clear_concepts_and_prerequisites(self, user_id: str):
        """Purge concepts, prerequisites, misconceptions, and evidence for a user to cleanly initialize a new learning topic."""
        with self.session_factory() as session:
            session.query(DBConceptMastery).filter_by(learner_id=user_id).delete()
            session.query(DBPrerequisite).filter_by(learner_id=user_id).delete()
            session.query(DBMisconception).filter_by(learner_id=user_id).delete()
            session.query(DBEvidenceItem).filter_by(learner_id=user_id).delete()
            session.query(DBQuizAttempt).filter_by(learner_id=user_id).delete()
            session.commit()

    # ---------------------------------------------------------
    # Prerequisites
    # ---------------------------------------------------------
    def add_prerequisite(self, user_id: str, concept_name: str, prerequisite_name: str, weight: float = 1.0) -> PrerequisiteRelation:
        with self.session_factory() as session:
            db_prereq = (
                session.query(DBPrerequisite)
                .filter_by(learner_id=user_id, concept_name=concept_name, prerequisite_name=prerequisite_name)
                .first()
            )
            if not db_prereq:
                db_prereq = DBPrerequisite(
                    learner_id=user_id,
                    concept_name=concept_name,
                    prerequisite_name=prerequisite_name,
                    weight=weight,
                )
                session.add(db_prereq)
                session.commit()
            return PrerequisiteRelation(
                concept_name=db_prereq.concept_name,
                prerequisite_name=db_prereq.prerequisite_name,
                weight=db_prereq.weight,
            )

    def get_prerequisites(self, user_id: str) -> List[PrerequisiteRelation]:
        with self.session_factory() as session:
            items = session.query(DBPrerequisite).filter_by(learner_id=user_id).all()
            return [
                PrerequisiteRelation(
                    concept_name=item.concept_name,
                    prerequisite_name=item.prerequisite_name,
                    weight=item.weight,
                )
                for item in items
            ]

    # ---------------------------------------------------------
    # Misconceptions
    # ---------------------------------------------------------
    def add_misconception(self, misconception: MisconceptionItem) -> MisconceptionItem:
        with self.session_factory() as session:
            db_misc = DBMisconception(
                learner_id=misconception.learner_id,
                concept_name=misconception.concept_name,
                description=misconception.description,
                evidence_observation=misconception.evidence_observation,
                status=misconception.status.value,
                detected_at=misconception.detected_at,
                resolved_at=misconception.resolved_at,
                remediation_notes=misconception.remediation_notes,
            )
            session.add(db_misc)
            session.commit()
            session.refresh(db_misc)
            return self._to_misconception_item(db_misc)

    def resolve_misconception(self, misconception_id: int, notes: Optional[str] = None) -> Optional[MisconceptionItem]:
        with self.session_factory() as session:
            db_misc = session.query(DBMisconception).filter_by(id=misconception_id).first()
            if not db_misc:
                return None
            db_misc.status = MisconceptionStatus.RECTIFIED.value
            db_misc.resolved_at = datetime.utcnow()
            if notes:
                db_misc.remediation_notes = notes
            session.commit()
            session.refresh(db_misc)
            return self._to_misconception_item(db_misc)

    def get_active_misconceptions(self, user_id: str, concept_name: Optional[str] = None) -> List[MisconceptionItem]:
        with self.session_factory() as session:
            q = session.query(DBMisconception).filter_by(
                learner_id=user_id, status=MisconceptionStatus.ACTIVE.value
            )
            if concept_name:
                q = q.filter_by(concept_name=concept_name)
            items = q.all()
            return [self._to_misconception_item(item) for item in items]

    def get_all_misconceptions(self, user_id: str) -> List[MisconceptionItem]:
        with self.session_factory() as session:
            items = session.query(DBMisconception).filter_by(learner_id=user_id).order_by(desc(DBMisconception.detected_at)).all()
            return [self._to_misconception_item(item) for item in items]

    # ---------------------------------------------------------
    # Evidence Store
    # ---------------------------------------------------------
    def add_evidence(self, evidence: EvidenceItem) -> EvidenceItem:
        with self.session_factory() as session:
            db_ev = DBEvidenceItem(
                learner_id=evidence.learner_id,
                concept_name=evidence.concept_name,
                evidence_type=evidence.evidence_type.value,
                score=evidence.score,
                resource_url=evidence.resource_url,
                observation=evidence.observation,
                user_feedback_rating=evidence.user_feedback_rating,
                timestamp=evidence.timestamp or datetime.utcnow(),
            )
            session.add(db_ev)
            session.commit()
            session.refresh(db_ev)
            return self._to_evidence_item(db_ev)

    def get_evidence_for_concept(self, user_id: str, concept_name: str) -> List[EvidenceItem]:
        with self.session_factory() as session:
            items = (
                session.query(DBEvidenceItem)
                .filter_by(learner_id=user_id, concept_name=concept_name)
                .order_by(desc(DBEvidenceItem.timestamp))
                .all()
            )
            return [self._to_evidence_item(item) for item in items]

    def get_recent_evidence(self, user_id: str, limit: int = 20) -> List[EvidenceItem]:
        with self.session_factory() as session:
            items = (
                session.query(DBEvidenceItem)
                .filter_by(learner_id=user_id)
                .order_by(desc(DBEvidenceItem.timestamp))
                .limit(limit)
                .all()
            )
            return [self._to_evidence_item(item) for item in items]

    # ---------------------------------------------------------
    # Learning History
    # ---------------------------------------------------------
    def record_history(
        self,
        user_id: str,
        resource_url: str,
        title: str,
        format: str = "documentation",
        completed: bool = True,
        perceived_difficulty: Optional[str] = None,
        usefulness_rating: Optional[int] = None,
    ):
        with self.session_factory() as session:
            entry = DBLearningHistory(
                learner_id=user_id,
                resource_url=resource_url,
                title=title,
                format=format,
                completed=completed,
                perceived_difficulty=perceived_difficulty,
                usefulness_rating=usefulness_rating,
                timestamp=datetime.utcnow(),
            )
            session.add(entry)
            session.commit()

    # ---------------------------------------------------------
    # Learning Journeys / Search History & Progress
    # ---------------------------------------------------------
    def record_learning_journey(
        self,
        learner_id: str,
        topic_title: str,
        learning_goal: str,
        target_outcome: str,
        path: LearningPath,
    ):
        from cognitive_learning_agent.memory.similarity import compute_topic_similarity

        with self.session_factory() as session:
            # Check for existing journey by exact title or high topic similarity
            existing = (
                session.query(DBLearningJourney)
                .filter_by(learner_id=learner_id, topic_title=topic_title)
                .first()
            )
            if not existing:
                all_j = session.query(DBLearningJourney).filter_by(learner_id=learner_id).all()
                for j in all_j:
                    is_match, score = compute_topic_similarity(topic_title, j.topic_title)
                    if is_match and score >= 0.85:
                        existing = j
                        break

            path_dict = path.model_dump(mode="json") if hasattr(path, "model_dump") else path.dict()
            path_str = json.dumps(path_dict)
            total = len(path.resources) if path.resources else len(path.ordered_concepts)

            if existing:
                existing.learning_goal = learning_goal
                existing.target_outcome = target_outcome
                existing.path_json = path_str
                existing.total_topics = total
                existing.updated_at = datetime.utcnow()
            else:
                entry = DBLearningJourney(
                    learner_id=learner_id,
                    topic_title=topic_title,
                    learning_goal=learning_goal,
                    target_outcome=target_outcome,
                    path_json=path_str,
                    total_topics=total,
                    completed_topics=0,
                    mastery_percentage=0.0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(entry)
            session.commit()

    def find_similar_learning_journey(self, query: str, learner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find an existing learning journey matching the topic query via semantic/lexical similarity."""
        from cognitive_learning_agent.memory.similarity import compute_topic_similarity

        all_journeys = self.get_learning_journeys(learner_id)
        if not all_journeys and learner_id:
            # If nothing found for learner_id, search global journey history
            all_journeys = self.get_learning_journeys()

        best_journey = None
        best_score = 0.0

        for j in all_journeys:
            candidates = [j.get("topic_title"), j.get("learning_goal"), j.get("target_outcome")]
            for cand in candidates:
                if not cand:
                    continue
                is_match, score = compute_topic_similarity(query, cand)
                if is_match and score > best_score:
                    best_score = score
                    best_journey = j

        if best_journey and best_score >= 0.65:
            return best_journey
        return None

    def deduplicate_learning_journeys(self):
        """Deduplicate existing learning journeys based on topic similarity."""
        from cognitive_learning_agent.memory.similarity import compute_topic_similarity

        with self.session_factory() as session:
            journeys = session.query(DBLearningJourney).order_by(DBLearningJourney.updated_at.desc()).all()
            kept = []
            to_delete = []

            for j in journeys:
                matched = False
                for k in kept:
                    is_match, score = compute_topic_similarity(j.topic_title, k.topic_title)
                    if is_match and score >= 0.80:
                        matched = True
                        # If j has higher progress, transfer it to k
                        if j.mastery_percentage > k.mastery_percentage:
                            k.mastery_percentage = j.mastery_percentage
                            k.completed_topics = max(k.completed_topics, j.completed_topics)
                        if j.path_json and not k.path_json:
                            k.path_json = j.path_json
                        to_delete.append(j)
                        break
                if not matched:
                    kept.append(j)

            for d in to_delete:
                session.delete(d)
            session.commit()

    def get_learning_journeys(self, learner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.session_factory() as session:
            query = session.query(DBLearningJourney)
            if learner_id and learner_id.strip():
                query = query.filter_by(learner_id=learner_id.strip())
            items = query.order_by(desc(DBLearningJourney.updated_at)).all()
            results = []
            for item in items:
                concepts = (
                    session.query(DBConceptMastery)
                    .filter_by(learner_id=item.learner_id)
                    .all()
                )
                if concepts:
                    total_c = len(concepts)
                    mastered_c = sum(1 for c in concepts if c.status == ConceptStatus.MASTERED.value or c.mastery_score >= 0.70)
                    attempted_c = sum(1 for c in concepts if c.evidence_count > 0 or c.status != ConceptStatus.NOT_STARTED.value)
                    avg_mastery = sum(c.mastery_score for c in concepts) / total_c
                    progress_pct = round(avg_mastery * 100, 1)
                else:
                    total_c = item.total_topics or 1
                    mastered_c = item.completed_topics
                    attempted_c = item.completed_topics
                    progress_pct = round(item.mastery_percentage, 1)

                results.append({
                    "id": item.id,
                    "learner_id": item.learner_id,
                    "topic_title": item.topic_title,
                    "learning_goal": item.learning_goal,
                    "target_outcome": item.target_outcome,
                    "path_json": item.path_json,
                    "total_topics": total_c,
                    "completed_topics": mastered_c,
                    "attempted_topics": attempted_c,
                    "progress_percentage": progress_pct,
                    "mastery_percentage": progress_pct,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                })
            return results

    def update_journey_progress(self, learner_id: str, topic_title: str, completed_increment: int = 1, mastery_pct: float = 0.0):
        with self.session_factory() as session:
            journey = None
            if learner_id and learner_id.strip():
                journey = (
                    session.query(DBLearningJourney)
                    .filter_by(learner_id=learner_id.strip(), topic_title=topic_title)
                    .first()
                )
                if not journey:
                    journey = (
                        session.query(DBLearningJourney)
                        .filter(DBLearningJourney.learner_id == learner_id.strip())
                        .order_by(desc(DBLearningJourney.updated_at))
                        .first()
                    )
            if not journey:
                journey = (
                    session.query(DBLearningJourney)
                    .order_by(desc(DBLearningJourney.updated_at))
                    .first()
                )
            if journey:
                if completed_increment > 0:
                    journey.completed_topics = min(journey.total_topics, journey.completed_topics + completed_increment)
                if mastery_pct > 0:
                    journey.mastery_percentage = max(journey.mastery_percentage, mastery_pct)
                journey.updated_at = datetime.utcnow()
                session.commit()

    # ---------------------------------------------------------
    # Full Snapshot
    # ---------------------------------------------------------
    def get_cognitive_state_snapshot(self, user_id: str) -> Optional[CognitiveStateSnapshot]:
        learner = self.get_learner(user_id)
        if not learner:
            return None
        concepts = self.get_concept_masteries(user_id)
        prereqs = self.get_prerequisites(user_id)
        all_misconceptions = self.get_all_misconceptions(user_id)
        active_misc = [m for m in all_misconceptions if m.status == MisconceptionStatus.ACTIVE]
        rectified_misc = [m for m in all_misconceptions if m.status == MisconceptionStatus.RECTIFIED]
        recent_ev = self.get_recent_evidence(user_id, limit=15)

        # Progress computation
        if concepts:
            avg_mastery = sum(c.mastery_score for c in concepts.values()) / len(concepts)
        else:
            avg_mastery = 0.0

        return CognitiveStateSnapshot(
            learner=learner,
            concepts=concepts,
            prerequisites=prereqs,
            active_misconceptions=active_misc,
            rectified_misconceptions=rectified_misc,
            recent_evidence=recent_ev,
            overall_progress=round(avg_mastery * 100, 1),
        )

    # ---------------------------------------------------------
    # Converters
    # ---------------------------------------------------------
    @staticmethod
    def _to_learner_profile(db: DBLearner) -> LearnerProfile:
        return LearnerProfile(
            user_id=db.user_id,
            name=db.name,
            learning_goal=db.learning_goal,
            current_level=db.current_level,
            preferred_format=db.preferred_format,
            target_outcome=db.target_outcome,
            preferred_language=db.preferred_language,
            created_at=db.created_at,
            updated_at=db.updated_at,
        )

    @staticmethod
    def _to_concept_item(db: DBConceptMastery) -> ConceptMasteryItem:
        return ConceptMasteryItem(
            concept_name=db.concept_name,
            mastery_score=db.mastery_score,
            confidence_score=db.confidence_score,
            status=ConceptStatus(db.status),
            evidence_count=db.evidence_count,
            last_evaluated_at=db.last_evaluated_at,
            notes=db.notes,
        )

    @staticmethod
    def _to_misconception_item(db: DBMisconception) -> MisconceptionItem:
        return MisconceptionItem(
            id=db.id,
            learner_id=db.learner_id,
            concept_name=db.concept_name,
            description=db.description,
            evidence_observation=db.evidence_observation,
            status=MisconceptionStatus(db.status),
            detected_at=db.detected_at,
            resolved_at=db.resolved_at,
            remediation_notes=db.remediation_notes,
        )

    @staticmethod
    def _to_evidence_item(db: DBEvidenceItem) -> EvidenceItem:
        return EvidenceItem(
            id=db.id,
            learner_id=db.learner_id,
            concept_name=db.concept_name,
            evidence_type=EvidenceType(db.evidence_type),
            score=db.score,
            resource_url=db.resource_url,
            observation=db.observation,
            user_feedback_rating=db.user_feedback_rating,
            timestamp=db.timestamp,
        )

    # ---------------------------------------------------------
    # Quiz Attempt History
    # ---------------------------------------------------------
    def record_quiz_attempt(self, attempt: QuizAttemptRecord) -> QuizAttemptRecord:
        with self.session_factory() as session:
            db_attempt = DBQuizAttempt(
                learner_id=attempt.learner_id,
                concept_name=attempt.concept_name,
                subtopic_name=attempt.subtopic_name,
                attempt_number=attempt.attempt_number,
                score=attempt.score,
                passed=attempt.passed,
                total_questions=attempt.total_questions,
                correct_count=attempt.correct_count,
                quiz_type=attempt.quiz_type,
                questions_data=json.dumps(attempt.questions_data),
                weak_areas=json.dumps(attempt.weak_areas),
                misconceptions=json.dumps(attempt.misconceptions),
                recommended_resources=json.dumps(attempt.recommended_resources),
                remediation_efficacy=json.dumps(attempt.remediation_efficacy) if attempt.remediation_efficacy else None,
                next_action=attempt.next_action.value if hasattr(attempt.next_action, "value") else str(attempt.next_action),
                next_action_reason=attempt.next_action_reason,
                timestamp=attempt.timestamp or datetime.utcnow(),
            )
            session.add(db_attempt)
            session.commit()
            session.refresh(db_attempt)
            return self._to_quiz_attempt_record(db_attempt)

    def get_quiz_attempts(
        self,
        learner_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[QuizAttemptRecord]:
        target_id = learner_id or user_id
        with self.session_factory() as session:
            q = session.query(DBQuizAttempt).filter_by(learner_id=target_id)
            if concept_name:
                q = q.filter_by(concept_name=concept_name)
            items = q.order_by(DBQuizAttempt.attempt_number.asc()).all()
            return [self._to_quiz_attempt_record(it) for it in items]

    def get_latest_quiz_attempt(
        self,
        learner_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[QuizAttemptRecord]:
        target_id = learner_id or user_id
        with self.session_factory() as session:
            q = session.query(DBQuizAttempt).filter_by(learner_id=target_id)
            if concept_name:
                q = q.filter_by(concept_name=concept_name)
            item = q.order_by(desc(DBQuizAttempt.attempt_number)).first()
            return self._to_quiz_attempt_record(item) if item else None

    def count_quiz_attempts(
        self,
        learner_id: Optional[str] = None,
        concept_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> int:
        target_id = learner_id or user_id
        with self.session_factory() as session:
            q = session.query(DBQuizAttempt).filter_by(learner_id=target_id)
            if concept_name:
                q = q.filter_by(concept_name=concept_name)
            return q.count()

    @staticmethod
    def _to_quiz_attempt_record(db: DBQuizAttempt) -> QuizAttemptRecord:
        return QuizAttemptRecord(
            id=db.id,
            learner_id=db.learner_id,
            concept_name=db.concept_name,
            subtopic_name=db.subtopic_name,
            attempt_number=db.attempt_number,
            score=db.score,
            passed=db.passed,
            total_questions=db.total_questions,
            correct_count=db.correct_count,
            quiz_type=db.quiz_type or "initial",
            questions_data=json.loads(db.questions_data) if db.questions_data else [],
            weak_areas=json.loads(db.weak_areas) if db.weak_areas else [],
            misconceptions=json.loads(db.misconceptions) if db.misconceptions else [],
            recommended_resources=json.loads(db.recommended_resources) if db.recommended_resources else [],
            remediation_efficacy=json.loads(db.remediation_efficacy) if db.remediation_efficacy else None,
            next_action=NextLearningAction(db.next_action) if db.next_action else NextLearningAction.PROCEED,
            next_action_reason=db.next_action_reason,
            timestamp=db.timestamp,
        )

