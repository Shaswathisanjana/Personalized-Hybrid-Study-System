"""Learning Agent with Cognitive Memory orchestrating the complete 7-step Learning Loop."""

import logging
from datetime import datetime
from typing import Tuple, Optional, Dict, Any, List

from cognitive_learning_agent.memory.database import get_db_session, init_db
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.cognitive_engine.evidence_store import EvidenceStore
from cognitive_learning_agent.cognitive_engine.mastery_engine import MasteryEngine
from cognitive_learning_agent.cognitive_engine.misconception_manager import MisconceptionManager
from cognitive_learning_agent.cognitive_engine.conflict_detector import ConflictDetectorResolver
from cognitive_learning_agent.cognitive_engine.prerequisite_graph import PrerequisiteGraph
from cognitive_learning_agent.cognitive_engine.replanner import AgentReplanner
from cognitive_learning_agent.discovery.searcher import ResourceSearcher
from cognitive_learning_agent.discovery.extractor import PageExtractor
from cognitive_learning_agent.discovery.validator import LinkValidator
from cognitive_learning_agent.discovery.ranker import ResourceRanker
from cognitive_learning_agent.llm.client import LLMClient
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    LearnerProfile,
    ConceptMasteryItem,
    ConceptStatus,
    LearningResource,
    LearningPath,
    AssessmentFeedback,
    CognitiveStateSnapshot,
    ReplanResult,
    DifficultyLevel,
    LearningFormat,
    ConceptQuiz,
    QuizQuestion,
    QuizSubmission,
    QuizEvaluationResult,
    QuestionType,
    QuizAttemptRecord,
    NextLearningAction,
)

logger = logging.getLogger(__name__)


class LearningAgent:
    """Agent that guides a user's learning journey by discovering real online resources

    and continuously adapting the curriculum based on a persistent cognitive state.
    """

    def __init__(
        self,
        repository: Optional[CognitiveMemoryRepository] = None,
        llm_client: Optional[LLMClient] = None,
        searcher: Optional[ResourceSearcher] = None,
        extractor: Optional[PageExtractor] = None,
        validator: Optional[LinkValidator] = None,
        ranker: Optional[ResourceRanker] = None,
        db_url: Optional[str] = None,
    ):
        if db_url:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from contextlib import contextmanager
            from cognitive_learning_agent.models.db_models import Base
            custom_engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
                echo=False,
            )
            Base.metadata.create_all(bind=custom_engine)
            custom_session_local = sessionmaker(autocommit=False, autoflush=False, bind=custom_engine)

            @contextmanager
            def custom_session_factory():
                session = custom_session_local()
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise
                finally:
                    session.close()

            self.repository = CognitiveMemoryRepository(custom_session_factory)
        else:
            # Initialize Database schema if needed
            init_db()
            self.repository = repository or CognitiveMemoryRepository(get_db_session)

        self.repo = self.repository
        self.llm = llm_client or LLMClient()
        self.searcher = searcher or ResourceSearcher()
        self.extractor = extractor or PageExtractor()
        self.validator = validator or LinkValidator()
        self.ranker = ranker or ResourceRanker()

        # Cognitive Engine components
        self.evidence_store = EvidenceStore(self.repository)
        self.mastery_engine = MasteryEngine(self.repository)
        self.misconception_manager = MisconceptionManager(self.repository, self.llm)
        self.conflict_detector = ConflictDetectorResolver(self.repository)
        self.replanner = AgentReplanner(
            self.repository,
            self.searcher,
            self.extractor,
            self.validator,
            self.ranker,
        )

        # In-memory path cache per user
        self._current_paths: Dict[str, LearningPath] = {}
        # In-memory quiz cache per user:concept
        self._quiz_cache: Dict[str, ConceptQuiz] = {}

    # =========================================================================
    # Step 1-4: Onboarding & Initial Path Generation
    # =========================================================================
    def start_learning_journey(self, profile_data: LearnerProfileCreate) -> Tuple[LearnerProfile, LearningPath]:
        """Execute Steps 1 to 4:

        1. Understand Goal -> decompose goal into concept DAG
        2. Assess Prior Knowledge -> initialize cognitive state
        3. Discover and Rank Resources -> search DDG, extract metadata, validate, rank
        4. Recommend Learning Path -> construct ordered path with direct URLs
        """
        user_id = profile_data.user_id
        logger.info(f"Starting learning journey for user {user_id}: {profile_data.learning_goal}")

        # Save profile
        profile = self.repository.upsert_learner(profile_data)

        # Step 1: Understand Goal (Decomposition)
        curriculum = self.llm.decompose_goal(
            goal=profile.learning_goal,
            target_outcome=profile.target_outcome,
            current_level=profile.current_level.value,
            preferred_format=profile.preferred_format.value,
        )

        concepts_raw = curriculum.get("concepts", [])
        graph = PrerequisiteGraph()

        # Cleanly purge previous concepts and prerequisites to isolate this topic
        self.repository.clear_concepts_and_prerequisites(user_id)

        # Save concepts & prerequisites in DB
        for c in concepts_raw:
            c_name = c["name"]
            graph.add_concept(c_name)
            for prereq in c.get("prerequisites", []):
                self.repository.add_prerequisite(user_id, c_name, prereq)
                graph.add_prerequisite(c_name, prereq)

        # Step 2: Assess Prior Knowledge (Initialize Cognitive State)
        initial_score = 0.20 if profile.current_level == DifficultyLevel.BEGINNER else 0.40
        for c in concepts_raw:
            c_name = c["name"]
            item = ConceptMasteryItem(
                concept_name=c_name,
                mastery_score=initial_score if c.get("difficulty") == "beginner" else 0.05,
                confidence_score=0.20,
                status=ConceptStatus.NOT_STARTED,
                evidence_count=0,
                last_evaluated_at=datetime.utcnow(),
                notes=f"Initial concept initialized from goal decomposition.",
            )
            self.repository.upsert_concept_mastery(user_id, item)

        # Step 3 & 4: Discover, Validate, Rank, and Assemble Learning Path (URL for each Topic)
        ordered_concepts = graph.topological_sort()
        path_resources: List[LearningResource] = []
        seen_urls = set()

        for c_name in ordered_concepts:
            # Discover resources online targeted specifically to this topic
            raw_results = self.searcher.search_for_concept(
                concept_name=c_name,
                goal=profile.learning_goal,
                preferred_format=profile.preferred_format,
                difficulty=profile.current_level,
                preferred_language=profile.preferred_language or "Python",
            )
            # Validate links & remove duplicates
            validated = self.validator.validate_and_deduplicate(raw_results)

            # Extract rich metadata
            enriched = []
            for item in validated[:3]:
                meta = self.extractor.extract_metadata(
                    url=item["url"],
                    initial_title=item.get("title", ""),
                    initial_snippet=item.get("snippet", ""),
                )
                item.update(meta)
                enriched.append(item)

            # Rank by semantic relevance + difficulty alignment
            ranked = self.ranker.rank_resources(
                candidate_items=enriched if enriched else validated,
                target_concept=c_name,
                learning_goal=profile.learning_goal,
                learner_level=profile.current_level,
                preferred_format=profile.preferred_format,
            )

            # Assign strictly 1 top verified tutorial resource for this distinct subtopic
            assigned = False
            for r in ranked:
                if r.url not in seen_urls:
                    r.target_concept = c_name
                    path_resources.append(r)
                    seen_urls.add(r.url)
                    assigned = True
                    break

            if not assigned and ranked:
                r = ranked[0]
                r.target_concept = c_name
                path_resources.append(r)

        total_est_minutes = sum(r.estimated_minutes for r in path_resources)

        path = LearningPath(
            learner_id=user_id,
            goal=profile.learning_goal,
            target_outcome=profile.target_outcome,
            resources=path_resources,
            ordered_concepts=ordered_concepts,
            rationale=curriculum.get(
                "learning_strategy",
                f"Personalized path targeting: {profile.target_outcome} with {len(path_resources)} online resources.",
            ),
            estimated_total_minutes=total_est_minutes,
        )

        self._current_paths[user_id] = path
        self.repository.save_learning_path(user_id, path)
        topic_title = profile.target_outcome or profile.learning_goal
        self.repository.record_learning_journey(
            learner_id=user_id,
            topic_title=topic_title,
            learning_goal=profile.learning_goal,
            target_outcome=profile.target_outcome,
            path=path,
        )
        return profile, path

    def find_similar_learning_journey(self, query: str, learner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find an existing learning journey matching the topic query via semantic/lexical similarity."""
        if hasattr(self.repository, "find_similar_learning_journey"):
            return self.repository.find_similar_learning_journey(query, learner_id)
        return None

    def deduplicate_learning_journeys(self):
        """Deduplicate existing learning journeys based on topic similarity."""
        if hasattr(self.repository, "deduplicate_learning_journeys"):
            self.repository.deduplicate_learning_journeys()

    # =========================================================================
    # Step 5-7: Feedback Collection, Memory Update, and Adaptive Replanning
    # =========================================================================
    def process_feedback(self, feedback: AssessmentFeedback) -> ReplanResult:
        """Execute Steps 5 to 7:

        5. Collect Learning Evidence -> persist atomic observations
        6. Update Cognitive Memory -> conflict check, mastery recalculation, misconception resolution
        7. Replan Recommendations -> dynamically adapt curriculum based on cognitive state
        """
        user_id = feedback.learner_id
        logger.info(f"Processing feedback for user {user_id} on {feedback.concept_name}")

        # Step 5: Collect Learning Evidence
        evidence_items = self.evidence_store.record_feedback(feedback)

        # Step 6: Update Cognitive Memory
        # A. Conflict Detection
        conflicts = self.conflict_detector.detect_and_resolve(feedback)

        # B. Misconception Processing
        self.misconception_manager.process_feedback(feedback)

        # C. Mastery Recalculation (Bayesian/EWMA)
        self.mastery_engine.update_concept_mastery(user_id, feedback.concept_name)

        # Step 7: Replan Recommendations
        current_path = self._current_paths.get(user_id) or self.repository.get_learning_path(user_id)
        if not current_path:
            # Reconstruct from snapshot if session restarted
            snapshot = self.repository.get_cognitive_state_snapshot(user_id)
            if not snapshot:
                profile_data = LearnerProfileCreate(
                    user_id=user_id,
                    name=user_id,
                    learning_goal=feedback.concept_name,
                    current_level=DifficultyLevel.BEGINNER,
                    target_outcome=feedback.concept_name,
                )
                self.repository.upsert_learner(profile_data)
                snapshot = self.repository.get_cognitive_state_snapshot(user_id)
            goal_val = snapshot.learner.learning_goal if snapshot and snapshot.learner else feedback.concept_name
            outcome_val = snapshot.learner.target_outcome if snapshot and snapshot.learner else feedback.concept_name
            concepts_val = list(snapshot.concepts.keys()) if snapshot and snapshot.concepts else [feedback.concept_name]
            current_path = LearningPath(
                learner_id=user_id,
                goal=goal_val,
                target_outcome=outcome_val,
                ordered_concepts=concepts_val,
            )

        active_misc = self.repository.get_active_misconceptions(user_id)

        replan_result = self.replanner.replan(
            user_id=user_id,
            current_path=current_path,
            latest_feedback=feedback,
            detected_conflicts=conflicts,
            active_misconceptions=active_misc,
        )

        # Update cached path and persist to database
        self._current_paths[user_id] = replan_result.updated_learning_path
        self.repository.save_learning_path(user_id, replan_result.updated_learning_path)

        return replan_result

    # =========================================================================
    # Cognitive State Inspection & Path Reconstruction
    # =========================================================================
    def get_cognitive_state(self, user_id: str) -> Optional[CognitiveStateSnapshot]:
        """Fetch complete transparent cognitive state snapshot for dashboard/UI."""
        return self.repository.get_cognitive_state_snapshot(user_id)

    def get_current_learning_path(self, user_id: str) -> Optional[LearningPath]:
        """Get the current recommended learning path for a learner."""
        # 1. In-memory path
        if user_id in self._current_paths and self._current_paths[user_id].resources:
            return self._ensure_distinct_comprehensive_path(user_id, self._current_paths[user_id])

        # 2. Persisted path from database
        persisted = self.repository.get_learning_path(user_id)
        if persisted and persisted.resources:
            cleaned = self._ensure_distinct_comprehensive_path(user_id, persisted)
            self._current_paths[user_id] = cleaned
            return cleaned

        # 3. Auto-reconstruct if learner concepts exist
        return self.reconstruct_or_discover_path(user_id)

    def _is_concept_relevant_to_goal(self, concept_name: str, goal: str, target_outcome: str = "") -> bool:
        """Check whether a concept is relevant to the learning goal and target outcome,
        preventing cross-domain contamination (e.g. graph algorithms in tree curricula).
        """
        c_lower = concept_name.lower().strip()
        combined_target = f"{goal} {target_outcome}".lower()

        # Specific domain conflict resolution:
        # Case A: Learning Goal is specifically about Trees (and not Graphs)
        target_has_tree = any(k in combined_target for k in ["tree", "bst", "avl", "trie", "heap"])
        target_has_graph = "graph" in combined_target or "network" in combined_target

        if target_has_tree and not target_has_graph:
            # Exclude Graph concepts
            graph_markers = [
                "graph", "shortest path", "spanning tree", "connectivity", "bipartite",
                "topological sort", "dijkstra", "bellman", "floyd", "kruskal", "prim"
            ]
            if any(gm in c_lower for gm in graph_markers):
                return False

        # Case B: Learning Goal is specifically about Graphs (and not Trees)
        if target_has_graph and not target_has_tree:
            tree_markers = [
                "binary tree", "binary search tree", "bst", "avl", "red-black", "b-tree", "segment tree", "fenwick"
            ]
            if any(tm in c_lower for tm in tree_markers):
                return False

        return True

    def _ensure_distinct_comprehensive_path(self, user_id: str, path: LearningPath) -> LearningPath:
        """Ensure that every topic in the learning path is distinct and all subtopics from

        the learner's curriculum/snapshot are covered with exactly 1 primary resource.
        """
        snapshot = self.repository.get_cognitive_state_snapshot(user_id)
        if not snapshot:
            return path

        goal = path.goal or (snapshot.learner.learning_goal if snapshot.learner else "")
        target = path.target_outcome or (snapshot.learner.target_outcome if snapshot.learner else "")

        if path.ordered_concepts:
            ordered = [c for c in path.ordered_concepts if self._is_concept_relevant_to_goal(c, goal, target)]
        else:
            ordered = [c for c in snapshot.concepts.keys() if self._is_concept_relevant_to_goal(c, goal, target)]

        if not ordered:
            ordered = [c for c in snapshot.concepts.keys() if self._is_concept_relevant_to_goal(c, goal, target)]
        if not ordered:
            ordered = list(snapshot.concepts.keys())

        # 1. Deduplicate existing resources by target_concept (keep first/best)
        concept_to_resource: Dict[str, LearningResource] = {}
        for r in path.resources:
            c = r.target_concept
            if c and c not in concept_to_resource and self._is_concept_relevant_to_goal(c, goal, target):
                concept_to_resource[c] = r

        # 2. Check if all ordered subtopics are present; discover for any missing subtopic
        missing_concepts = [c for c in ordered if c not in concept_to_resource]
        if missing_concepts:
            for c_name in missing_concepts:
                raw_results = self.searcher.search_for_concept(
                    concept_name=c_name,
                    goal=snapshot.learner.learning_goal,
                    preferred_format=snapshot.learner.preferred_format,
                    difficulty=snapshot.learner.current_level,
                    preferred_language=snapshot.learner.preferred_language or "Python",
                )
                validated = self.validator.validate_and_deduplicate(raw_results)
                ranked = self.ranker.rank_resources(
                    candidate_items=validated,
                    target_concept=c_name,
                    learning_goal=snapshot.learner.learning_goal,
                    learner_level=snapshot.learner.current_level,
                    preferred_format=snapshot.learner.preferred_format,
                )
                if ranked:
                    r = ranked[0]
                    r.target_concept = c_name
                    concept_to_resource[c_name] = r
                else:
                    # Educational resource fallback for completeness
                    concept_to_resource[c_name] = LearningResource(
                        url=f"https://www.geeksforgeeks.org/{c_name.lower().replace(' ', '-')}/",
                        title=f"{c_name} Tutorial",
                        snippet=f"Comprehensive guide and problem solving for {c_name}.",
                        domain="geeksforgeeks.org",
                        format=snapshot.learner.preferred_format or LearningFormat.DOCUMENTATION,
                        difficulty=snapshot.learner.current_level or DifficultyLevel.BEGINNER,
                        target_concept=c_name,
                        relevance_score=0.9,
                        estimated_minutes=15,
                    )

        # 3. Assemble distinct ordered resources covering all subtopics
        distinct_resources: List[LearningResource] = []
        for c in ordered:
            if c in concept_to_resource:
                distinct_resources.append(concept_to_resource[c])

        # If any extra concepts were in concept_to_resource not in ordered
        for c, r in concept_to_resource.items():
            if c not in ordered and r not in distinct_resources and self._is_concept_relevant_to_goal(c, goal, target):
                distinct_resources.append(r)

        total_est = sum(r.estimated_minutes for r in distinct_resources)
        path.resources = distinct_resources
        path.ordered_concepts = ordered
        path.estimated_total_minutes = total_est

        # Persist cleaned path to DB and journeys
        self._current_paths[user_id] = path
        self.repository.save_learning_path(user_id, path)
        topic_title = snapshot.learner.target_outcome or snapshot.learner.learning_goal
        self.repository.record_learning_journey(
            learner_id=user_id,
            topic_title=topic_title,
            learning_goal=snapshot.learner.learning_goal,
            target_outcome=snapshot.learner.target_outcome,
            path=path,
        )
        return path

    def reconstruct_or_discover_path(self, user_id: str) -> Optional[LearningPath]:
        """Reconstruct or discover verified online resources for all curriculum concepts."""
        snapshot = self.repository.get_cognitive_state_snapshot(user_id)
        if not snapshot or not snapshot.concepts:
            return None

        goal = snapshot.learner.learning_goal or ""
        target = snapshot.learner.target_outcome or ""

        # Filter concepts to only those relevant to the learner's goal
        relevant_concepts = [
            c_name for c_name in snapshot.concepts.keys()
            if self._is_concept_relevant_to_goal(c_name, goal, target)
        ]
        if not relevant_concepts:
            relevant_concepts = list(snapshot.concepts.keys())

        # Build DAG
        graph = PrerequisiteGraph()
        for c_name in relevant_concepts:
            graph.add_concept(c_name)
        for p in snapshot.prerequisites:
            if p.concept_name in relevant_concepts and p.prerequisite_name in relevant_concepts:
                graph.add_prerequisite(p.concept_name, p.prerequisite_name)

        ordered_concepts = graph.topological_sort()
        if not ordered_concepts:
            ordered_concepts = relevant_concepts

        path_resources: List[LearningResource] = []
        seen_urls = set()
        seen_concepts = set()

        for c_name in ordered_concepts:
            if c_name in seen_concepts:
                continue

            raw_results = self.searcher.search_for_concept(
                concept_name=c_name,
                goal=snapshot.learner.learning_goal,
                preferred_format=snapshot.learner.preferred_format,
                difficulty=snapshot.learner.current_level,
                preferred_language=snapshot.learner.preferred_language or "Python",
            )
            validated = self.validator.validate_and_deduplicate(raw_results)
            enriched = []
            for item in validated[:3]:
                meta = self.extractor.extract_metadata(
                    url=item["url"],
                    initial_title=item.get("title", ""),
                    initial_snippet=item.get("snippet", ""),
                )
                item.update(meta)
                enriched.append(item)

            ranked = self.ranker.rank_resources(
                candidate_items=enriched if enriched else validated,
                target_concept=c_name,
                learning_goal=snapshot.learner.learning_goal,
                learner_level=snapshot.learner.current_level,
                preferred_format=snapshot.learner.preferred_format,
            )

            assigned = False
            for r in ranked:
                if r.url not in seen_urls:
                    r.target_concept = c_name
                    path_resources.append(r)
                    seen_urls.add(r.url)
                    seen_concepts.add(c_name)
                    assigned = True
                    break

            if not assigned and ranked:
                r = ranked[0]
                r.target_concept = c_name
                path_resources.append(r)
                seen_concepts.add(c_name)
            elif not assigned:
                fallback = LearningResource(
                    url=f"https://www.geeksforgeeks.org/{c_name.lower().replace(' ', '-')}/",
                    title=f"{c_name} Tutorial",
                    snippet=f"Comprehensive guide and problem solving for {c_name}.",
                    domain="geeksforgeeks.org",
                    format=snapshot.learner.preferred_format or LearningFormat.DOCUMENTATION,
                    difficulty=snapshot.learner.current_level or DifficultyLevel.BEGINNER,
                    target_concept=c_name,
                    relevance_score=0.9,
                    estimated_minutes=15,
                )
                path_resources.append(fallback)
                seen_concepts.add(c_name)

        total_est_minutes = sum(r.estimated_minutes for r in path_resources)
        path = LearningPath(
            learner_id=user_id,
            goal=snapshot.learner.learning_goal,
            target_outcome=snapshot.learner.target_outcome,
            resources=path_resources,
            ordered_concepts=ordered_concepts,
            rationale=f"Curated learning path targeting: {snapshot.learner.target_outcome or snapshot.learner.learning_goal} with {len(path_resources)} validated resources.",
            estimated_total_minutes=total_est_minutes,
        )

        self._current_paths[user_id] = path
        self.repository.save_learning_path(user_id, path)
        topic_title = snapshot.learner.target_outcome or snapshot.learner.learning_goal
        self.repository.record_learning_journey(
            learner_id=user_id,
            topic_title=topic_title,
            learning_goal=snapshot.learner.learning_goal,
            target_outcome=snapshot.learner.target_outcome,
            path=path,
        )
        return path


    # =========================================================================
    # =========================================================================
    # Step 5b: Diagnostic & Adaptive Quizzes, Cognitive Memory & Next Actions
    # =========================================================================
    def generate_quiz_for_resource(
        self,
        user_id: str,
        concept_name: str,
        resource_url: Optional[str] = None,
        force_refresh: bool = False,
        attempt_number: Optional[int] = None,
        resource_context: str = "",
    ) -> ConceptQuiz:
        """Generate a diagnostic or adaptive quiz testing understanding of the resource's concept.

        Attempt 1: Standard initial diagnostic assessment (6 MCQs + 4 Descriptive).
        Attempt 2+: Cognitive memory adaptive retake quiz prioritizing previously missed concepts,
                    recurring misconceptions, predict output coding questions, and retention revision.
        """
        past_attempts = self.repository.get_quiz_attempts(user_id, concept_name)
        current_attempt_num = attempt_number or (len(past_attempts) + 1)

        cache_key = f"scope-v2:{user_id}:{concept_name}:{resource_url or chr(45)}:att_{current_attempt_num}"
        fallback_key = f"scope-v2:{user_id}:{concept_name}:{resource_url or chr(45)}"

        if not force_refresh:
            if cache_key in self._quiz_cache and bool(self._quiz_cache[cache_key].questions):
                return self._quiz_cache[cache_key]
            if current_attempt_num == 1 and fallback_key in self._quiz_cache and bool(self._quiz_cache[fallback_key].questions):
                return self._quiz_cache[fallback_key]

        snapshot = self.repository.get_cognitive_state_snapshot(user_id)
        level_str = snapshot.learner.current_level.value if snapshot and snapshot.learner else "beginner"

        # Adaptive Retake if attempt >= 2 and student has previous attempt history
        if current_attempt_num > 1 and past_attempts:
            mastered_concepts: List[str] = []
            if snapshot and snapshot.concepts:
                mastered_concepts = [
                    c_name for c_name, c_item in snapshot.concepts.items()
                    if (c_item.status == ConceptStatus.MASTERED or c_item.mastery_score >= 0.70)
                    and c_name != concept_name
                ]

            quiz = self.llm.generate_adaptive_quiz(
                concept_name=concept_name,
                previous_attempts=past_attempts,
                mastered_concepts=mastered_concepts,
                resource_title=(resource_url or "") + "\n" + resource_context,
                difficulty=level_str,
            )
        else:
            quiz = self.llm.generate_concept_quiz(
                concept_name=concept_name,
                resource_title=(resource_url or "") + "\n" + resource_context,
                difficulty=level_str,
            )

        from cognitive_learning_agent.llm.quiz_scope import validate_scope
        validate_scope(concept_name, quiz.questions)
        quiz.resource_url = resource_url
        quiz.attempt_number = current_attempt_num
        quiz.quiz_type = "adaptive_retake" if current_attempt_num >= 2 else "initial"
        self._quiz_cache[cache_key] = quiz
        self._quiz_cache[fallback_key] = quiz
        return quiz

    def evaluate_quiz_and_remedy(
        self,
        submission: Optional[QuizSubmission] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> QuizEvaluationResult:
        """Evaluate quiz responses, diagnose weak areas and misconceptions,

        update cognitive memory, track remediation efficacy across attempts,
        determine next learning action (PROCEED / REVISE / REVISIT_PREREQUISITE),
        and discover targeted online learning resources covering weak areas.
        """
        if submission is None:
            if "submission" in kwargs:
                submission = kwargs["submission"]
            else:
                submission = QuizSubmission(**kwargs)
        if user_id and not submission.learner_id:
            submission.learner_id = user_id

        user_id = submission.learner_id
        concept_name = submission.concept_name

        past_attempts = self.repository.get_quiz_attempts(user_id, concept_name)
        attempt_number = submission.attempt_number or (len(past_attempts) + 1)
        cache_key = f"scope-v2:{user_id}:{concept_name}:{submission.resource_url or chr(45)}:att_{attempt_number}"
        fallback_key = f"scope-v2:{user_id}:{concept_name}:{submission.resource_url or chr(45)}"

        quiz = self._quiz_cache.get(cache_key) or self._quiz_cache.get(fallback_key)
        if not quiz or not quiz.questions:
            raise ValueError("This quiz session expired. Reopen the quiz before submitting answers; an unseen quiz will not be substituted.")

        total_questions = len(quiz.questions)
        correct_count = 0
        total_earned_score = 0.0
        question_feedback: List[Dict[str, Any]] = []
        weak_areas: List[str] = []
        detected_misconceptions: List[str] = []

        for q in quiz.questions:
            q_type = getattr(q, "question_type", QuestionType.MCQ)
            is_descriptive = (q_type == QuestionType.DESCRIPTIVE)

            if is_descriptive:
                user_text = submission.descriptive_answers.get(q.question_id, "").strip()
                text_lower = user_text.lower()
                matched_kws = [kw for kw in q.rubric_keywords if kw.lower() in text_lower]
                missing_kws = [kw for kw in q.rubric_keywords if kw.lower() not in text_lower]
                word_count = len(user_text.split())

                if q.rubric_keywords:
                    match_ratio = len(matched_kws) / len(q.rubric_keywords)
                else:
                    match_ratio = 1.0 if word_count >= 15 else (word_count / 15.0)

                if match_ratio >= 0.50 and word_count >= 8:
                    q_score = 1.0
                    is_correct = True
                    correct_count += 1
                elif match_ratio >= 0.25 and word_count >= 4:
                    q_score = 0.5
                    is_correct = False
                else:
                    q_score = 0.0
                    is_correct = False

                total_earned_score += q_score

                if not is_correct:
                    weak_desc = f"{q.concept_aspect} (Conceptual Explanation)"
                    if weak_desc not in weak_areas:
                        weak_areas.append(weak_desc)
                    misc = f"Incomplete explanation of {q.concept_aspect}. Missing key conceptual principles: {', '.join(missing_kws[:3]) if missing_kws else 'insufficient depth'}"
                    if misc not in detected_misconceptions:
                        detected_misconceptions.append(misc)

                question_feedback.append({
                    "question_id": q.question_id,
                    "question_type": "descriptive",
                    "question_text": q.question_text,
                    "code_snippet": None,
                    "is_correct": is_correct,
                    "score": q_score,
                    "user_answer": user_text if user_text else "(No answer provided)",
                    "ideal_answer": q.ideal_answer or q.explanation,
                    "rubric_keywords": q.rubric_keywords,
                    "matched_keywords": matched_kws,
                    "missing_keywords": missing_kws,
                    "explanation": q.explanation,
                    "concept_aspect": q.concept_aspect,
                    "misconception": None if is_correct else f"Missing key principles: {', '.join(missing_kws[:3]) if missing_kws else 'brief answer'}",
                    "is_revision": getattr(q, "is_revision", False),
                })
            else:
                user_choice = submission.selected_answers.get(q.question_id)
                is_correct = (user_choice == q.correct_option_index)

                chosen_text = (
                    q.options[user_choice]
                    if (user_choice is not None and 0 <= user_choice < len(q.options))
                    else "Not answered"
                )
                correct_text = q.options[q.correct_option_index] if (q.options and 0 <= q.correct_option_index < len(q.options)) else ""

                if is_correct:
                    correct_count += 1
                    total_earned_score += 1.0
                    question_feedback.append({
                        "question_id": q.question_id,
                        "question_type": q_type.value if hasattr(q_type, "value") else str(q_type),
                        "question_text": q.question_text,
                        "code_snippet": getattr(q, "code_snippet", None),
                        "is_correct": True,
                        "score": 1.0,
                        "user_choice": user_choice,
                        "user_choice_text": chosen_text,
                        "correct_choice_text": correct_text,
                        "explanation": q.explanation,
                        "concept_aspect": q.concept_aspect,
                        "misconception": None,
                        "is_revision": getattr(q, "is_revision", False),
                    })
                else:
                    misc = (
                        q.distractor_misconceptions.get(user_choice)
                        if user_choice is not None
                        else None
                    )
                    if not misc:
                        misc = f"Conceptual misunderstanding regarding {q.concept_aspect}"

                    if misc not in detected_misconceptions:
                        detected_misconceptions.append(misc)
                    if q.concept_aspect not in weak_areas:
                        weak_areas.append(q.concept_aspect)

                    question_feedback.append({
                        "question_id": q.question_id,
                        "question_type": q_type.value if hasattr(q_type, "value") else str(q_type),
                        "question_text": q.question_text,
                        "code_snippet": getattr(q, "code_snippet", None),
                        "is_correct": False,
                        "score": 0.0,
                        "user_choice": user_choice,
                        "user_choice_text": chosen_text,
                        "correct_choice_text": correct_text,
                        "explanation": q.explanation,
                        "concept_aspect": q.concept_aspect,
                        "misconception": misc,
                        "is_revision": getattr(q, "is_revision", False),
                    })

        score = (total_earned_score / total_questions) if total_questions > 0 else 0.0
        passed = score >= 0.70

        # Prior mastery before this attempt
        prior_concept_item = self.repository.get_concept_masteries(user_id).get(concept_name)
        prior_mastery = prior_concept_item.mastery_score if prior_concept_item else 0.0

        # Track remediation efficacy across attempts
        remediation_efficacy = None
        if past_attempts:
            last_attempt = past_attempts[-1]
            prior_weaks = set(last_attempt.weak_areas)
            current_weaks = set(weak_areas)
            improved = list(prior_weaks - current_weaks)
            unimproved = list(prior_weaks.intersection(current_weaks))
            if prior_weaks:
                progress_pct = int(round((len(improved) / len(prior_weaks)) * 100)) if prior_weaks else 100
                remediation_efficacy = {
                    "prior_attempt_number": last_attempt.attempt_number,
                    "prior_weak_areas": list(prior_weaks),
                    "resolved_areas": improved,
                    "improved_areas": improved,
                    "remaining_weak_areas": unimproved,
                    "still_weak_areas": unimproved,
                    "progress_percentage": progress_pct,
                    "efficacy_rate": round(len(improved) / len(prior_weaks), 2),
                    "status": "improved" if progress_pct > 0 else "needs_review",
                    "helped": len(improved) > 0,
                    "summary": f"Prior recommendations helped resolve {len(improved)} of {len(prior_weaks)} weak areas ({progress_pct}% improvement).",
                }

        # Determine next pedagogical learning action from cognitive memory
        prereqs = self.repository.get_prerequisites(user_id)
        concept_prereqs = [p.prerequisite_name for p in prereqs if p.concept_name == concept_name]
        all_masteries = self.repository.get_concept_masteries(user_id)
        weak_prereqs = [
            p for p in concept_prereqs
            if all_masteries.get(p) is None or all_masteries[p].mastery_score < 0.60
        ]

        if score >= 0.70:
            if weak_prereqs:
                next_action = NextLearningAction.REVISIT_PREREQUISITE
                next_action_reason = f"Quiz passed ({round(score * 100)}%), but foundational prerequisite '{weak_prereqs[0]}' has low mastery (<60%). Revisit prerequisite to strengthen your base before moving forward."
            else:
                next_action = NextLearningAction.PROCEED
                next_action_reason = f"Mastery threshold achieved ({round(score * 100)}%) and prerequisites are satisfied. Ready to proceed to the next subtopic!"
        elif score >= 0.40:
            next_action = NextLearningAction.REVISE
            next_action_reason = f"Partial mastery demonstrated ({round(score * 100)}%). Review the targeted remedial resources below and retake the quiz to consolidate understanding."
        else:
            if concept_prereqs:
                next_action = NextLearningAction.REVISIT_PREREQUISITE
                next_action_reason = f"Fundamental gaps detected ({round(score * 100)}%). Step back to prerequisite '{concept_prereqs[0]}' before retrying this subtopic."
            else:
                next_action = NextLearningAction.REVISE
                next_action_reason = f"Score ({round(score * 100)}%) is below passing threshold. Study the targeted remedial resources below before your next attempt."

        # Update Journey Progress
        curr_p = self._current_paths.get(user_id) or self.repository.get_learning_path(user_id)
        path_topic = (curr_p.target_outcome or curr_p.goal) if curr_p else concept_name
        self.repository.update_journey_progress(
            learner_id=user_id,
            topic_title=path_topic,
            completed_increment=1 if (passed and next_action == NextLearningAction.PROCEED) else 0,
            mastery_pct=round(score * 100, 1),
        )

        # Ingest feedback into persistent cognitive memory (Bayesian Knowledge Tracing)
        feedback_notes = f"Quiz Attempt #{attempt_number} for {concept_name} (Score: {round(score * 100)}%)."
        if weak_areas:
            feedback_notes += f" Weak areas identified: {', '.join(weak_areas)}."
        if detected_misconceptions:
            feedback_notes += f" Misconceptions observed: {'; '.join(detected_misconceptions)}."

        feedback = AssessmentFeedback(
            learner_id=user_id,
            concept_name=concept_name,
            resource_url=submission.resource_url,
            completed=True,
            quiz_score=score,
            perceived_difficulty="too_hard" if score < 0.5 else "just_right",
            usefulness_rating=4,
            confusion_reported=len(weak_areas) > 0,
            notes=feedback_notes,
        )

        replan_res = self.process_feedback(feedback)

        # Retrieve new updated mastery
        new_concept_item = self.repository.get_concept_masteries(user_id).get(concept_name)
        new_mastery = new_concept_item.mastery_score if new_concept_item else score

        # Discover targeted online learning resources covering weak areas
        targeted_resources: List[LearningResource] = []
        seen_urls = set()
        if submission.resource_url:
            seen_urls.add(submission.resource_url)

        snapshot = self.repository.get_cognitive_state_snapshot(user_id)
        learner_level = snapshot.learner.current_level if snapshot and snapshot.learner else DifficultyLevel.BEGINNER
        pref_format = snapshot.learner.preferred_format if snapshot and snapshot.learner else LearningFormat.ANY
        pref_lang = (snapshot.learner.preferred_language or "Python") if snapshot and snapshot.learner else "Python"

        if weak_areas or not passed:
            topics_to_remediate = weak_areas[:2] if weak_areas else [f"{concept_name} fundamentals"]

            for topic in topics_to_remediate:
                clean_topic = topic.strip()
                query_concept = clean_topic if any(k in clean_topic.lower() for k in ["tree", "graph", "async", "api", "traversal", "search"]) else f"{concept_name} {clean_topic}"

                raw_res = self.searcher.search_for_concept(
                    concept_name=query_concept,
                    goal=f"Remediate identified weakness in {clean_topic}",
                    preferred_format=pref_format,
                    difficulty=learner_level,
                    preferred_language=pref_lang,
                )
                validated = self.validator.validate_and_deduplicate(raw_res)

                ranked = self.ranker.rank_resources(
                    candidate_items=validated,
                    target_concept=clean_topic,
                    learning_goal=f"Remediate weak area {clean_topic} in {concept_name}",
                    learner_level=learner_level,
                    preferred_format=pref_format,
                )

                for r in ranked:
                    if r.url not in seen_urls and r.relevance_score >= 0.35:
                        r.target_concept = f"Remediation: {clean_topic}"
                        targeted_resources.append(r)
                        seen_urls.add(r.url)
                        if len(targeted_resources) >= 3:
                            break
                if len(targeted_resources) >= 3:
                    break

            if len(targeted_resources) < 2:
                fallback_items = self.searcher._get_curated_fallback(concept_name, pref_lang)
                ranked_fallbacks = self.ranker.rank_resources(
                    candidate_items=fallback_items,
                    target_concept=concept_name,
                    learning_goal=f"Remediate foundational concepts in {concept_name}",
                    learner_level=learner_level,
                    preferred_format=pref_format,
                )
                for r in ranked_fallbacks:
                    if r.url not in seen_urls:
                        r.target_concept = f"Remediation: {concept_name}"
                        targeted_resources.append(r)
                        seen_urls.add(r.url)
                        if len(targeted_resources) >= 3:
                            break

        # Persist full Quiz Attempt History
        attempt_record = QuizAttemptRecord(
            learner_id=user_id,
            concept_name=concept_name,
            subtopic_name=concept_name,
            attempt_number=attempt_number,
            score=score,
            passed=passed,
            total_questions=total_questions,
            correct_count=correct_count,
            quiz_type=quiz.quiz_type if hasattr(quiz, "quiz_type") else "initial",
            questions_data=question_feedback,
            weak_areas=weak_areas,
            misconceptions=detected_misconceptions,
            recommended_resources=[r.model_dump() for r in targeted_resources],
            remediation_efficacy=remediation_efficacy,
            next_action=next_action,
            next_action_reason=next_action_reason,
            timestamp=datetime.utcnow(),
        )
        self.repository.record_quiz_attempt(attempt_record)

        return QuizEvaluationResult(
            concept_name=concept_name,
            attempt_number=attempt_number,
            quiz_type=quiz.quiz_type if hasattr(quiz, "quiz_type") else "initial",
            total_questions=total_questions,
            correct_count=correct_count,
            score=score,
            passed=passed,
            question_feedback=question_feedback,
            weak_areas=weak_areas,
            detected_misconceptions=detected_misconceptions,
            targeted_resources=targeted_resources,
            remediation_efficacy=remediation_efficacy,
            next_action=next_action,
            next_action_reason=next_action_reason,
            prior_mastery=prior_mastery,
            new_mastery=new_mastery,
            replan_result=replan_res,
        )


