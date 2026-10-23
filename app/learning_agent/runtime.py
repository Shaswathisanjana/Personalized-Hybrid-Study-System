from dataclasses import dataclass
from app.cognitive.assessment_transaction import assessment, once, persist, lock_for

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine

from app.learning_agent.agent import LearningAgent

from app.learning_agent.executor import (
    LearningActionExecutor,
    LearningActivity,
)

from app.learning_agent.content_generator import (
    PersonalizedContentGenerator,
    GeneratedContent,
)

from app.learning_agent.content_provider import (
    ContentProvider,
    LocalContentProvider,
)

from app.learning_agent.resources.models import (
    ResourceRecommendation,
)

from app.learning_agent.resources.resource_recommender import (
    LearningResourceRecommender,
)

from app.learning_agent.gemini_quiz_generator import (
    GeminiQuizGenerator,
)

from app.learning_agent.answer_evaluator import (
    AnswerEvaluator,
)

from app.learning_agent.misconception_analyzer import (
    MisconceptionAnalyzer,
)

from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
    EvaluationResult,
)

from app.learning_agent.practice_session import (
    PracticeSession,
)

from app.learning_agent.practice_policy import (
    AdaptivePracticePolicy,
    PracticeDecision,
)


# ======================================================
# STUDENT-FACING LEARNING EXPERIENCE
# ======================================================

@dataclass
class LearningExperience:
    """
    Complete student-facing Learning Agent output.

    Contains:
    - personalized learning activity
    - CACM-aware external resource recommendations
    """

    activity: LearningActivity
    recommendations: ResourceRecommendation | None = None


# ======================================================
# SINGLE ASSESSMENT OUTCOME
# ======================================================

@dataclass
class LearningAssessmentOutcome:
    """
    Result after one Learning Agent question.

    Flow:

    answer
        ->
    evaluation
        ->
    misconception analysis
        ->
    cognitive evidence
        ->
    CACM update
        ->
    next pedagogical activity
    """

    question: QuizQuestion
    student_answer: StudentAnswer
    evaluation: EvaluationResult
    evidence: LearningEvidence
    cognitive_result: dict
    next_activity: LearningActivity | None


# ======================================================
# PRACTICE SESSION START
# ======================================================

@dataclass
class PracticeSessionStart:
    """
    Returned when a new adaptive practice session begins.
    """

    session: PracticeSession
    question: QuizQuestion
    decision: PracticeDecision


# ======================================================
# PRACTICE SESSION ANSWER OUTCOME
# ======================================================

@dataclass
class PracticeSessionOutcome:
    """
    Returned after one answer inside an adaptive
    practice session.

    If the session is not complete, next_question
    contains the automatically generated next question.

    If the session is complete, next_question is None
    and summary contains the final session summary.
    """

    session: PracticeSession

    assessment: LearningAssessmentOutcome

    next_question: QuizQuestion | None = None

    next_decision: PracticeDecision | None = None

    summary: "PracticeSessionSummary | None" = None


# ======================================================
# PRACTICE SESSION SUMMARY
# ======================================================

@dataclass
class PracticeSessionSummary:
    """
    Student-facing and professor-inspectable summary
    after an adaptive practice session.
    """

    concept_name: str

    questions_completed: int

    correct_answers: int

    partial_answers: int

    incorrect_answers: int

    average_performance: float

    final_mastery: float

    final_confidence: float

    misconception_hypotheses: list[str]

    next_activity: LearningActivity


class LearningAgentRuntime:
    """
    Runtime controller for the Learning Agent.

    Main cycle:

        Observe cognitive state
            ->
        Decide pedagogical action
            ->
        Generate personalized content
            ->
        Recommend resources
            ->
        Generate adaptive assessment
            ->
        Receive student answer
            ->
        Evaluate answer
            ->
        Analyze misconception hypothesis
            ->
        Create LearningEvidence
            ->
        Update CACM
            ->
        Re-observe updated state
            ->
        Re-plan

    Adaptive practice extends the same loop across
    multiple sequential questions.

    It does NOT create a separate cognitive model.
    """

    # --------------------------------------------------
    # DIFFICULTY -> NUMERIC EVIDENCE MAPPING
    # --------------------------------------------------
    #
    # Prototype heuristic values.
    # These should later be experimentally calibrated.
    # --------------------------------------------------

    DIFFICULTY_SCORE = {
        "easy": 0.30,
        "medium": 0.60,
        "hard": 0.85,
    }

    # --------------------------------------------------
    # PRACTICE EVIDENCE RELIABILITY
    # --------------------------------------------------
    #
    # Prototype heuristic.
    # --------------------------------------------------

    PRACTICE_RELIABILITY = 0.80

    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
        content_provider: ContentProvider | None = None,
        resource_recommender=None,
        quiz_generator=None,
        answer_evaluator=None,
        misconception_analyzer=None,
        practice_policy=None,
    ):
        self.cognitive_engine = cognitive_engine

        # ==================================================
        # PEDAGOGICAL DECISION MAKER
        # ==================================================

        self.agent = LearningAgent()

        # ==================================================
        # ACTIVITY EXECUTOR
        # ==================================================

        self.executor = LearningActionExecutor()

        # ==================================================
        # PERSONALIZED CONTENT REQUEST GENERATOR
        # ==================================================

        self.content_generator = (
            PersonalizedContentGenerator()
        )

        # ==================================================
        # STUDENT-FACING CONTENT PROVIDER
        # ==================================================

        self.content_provider = (
            content_provider
            if content_provider is not None
            else LocalContentProvider()
        )

        # ==================================================
        # RESOURCE RECOMMENDER
        # ==================================================

        self.resource_recommender = (
            resource_recommender
            if resource_recommender is not None
            else LearningResourceRecommender()
        )

        # ==================================================
        # ASSESSMENT COMPONENTS
        # ==================================================

        self.quiz_generator = (
            quiz_generator
            if quiz_generator is not None
            else GeminiQuizGenerator()
        )

        self.answer_evaluator = (
            answer_evaluator
            if answer_evaluator is not None
            else AnswerEvaluator()
        )

        self.misconception_analyzer = (
            misconception_analyzer
            if misconception_analyzer is not None
            else MisconceptionAnalyzer()
        )

        # ==================================================
        # ADAPTIVE PRACTICE POLICY
        # ==================================================

        self.practice_policy = (
            practice_policy
            if practice_policy is not None
            else AdaptivePracticePolicy()
        )

    # ==================================================
    # 1. OBSERVE -> DECIDE
    # ==================================================

    def choose_action(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ):
        """
        Observe shared cognitive state and choose the
        next pedagogical action.
        """

        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        has_conflict = (
            self.cognitive_engine.has_conflict(
                student.user_id,
                concept_name,
            )
        )

        return self.agent.choose_action(
            student=student,
            concept_name=concept_name,
            has_conflict=has_conflict,
        )

    # ==================================================
    # 2. BUILD PERSONALIZED CONTENT REQUEST
    # ==================================================

    def generate_personalized_content(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> GeneratedContent:
        """
        Build structured personalized content request.
        """

        action = self.choose_action(
            student=student,
            concept_name=concept_name,
        )

        return self.content_generator.generate(
            student=student,
            action=action,
        )

    # ==================================================
    # 3. GENERATE STUDENT-FACING ACTIVITY
    # ==================================================

    def get_next_activity(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> LearningActivity:
        """
        Execute the Learning Agent content cycle.
        """

        action = self.choose_action(
            student=student,
            concept_name=concept_name,
        )

        generated_request = (
            self.content_generator.generate(
                student=student,
                action=action,
            )
        )

        actual_content = (
            self.content_provider.create_content(
                generated_request
            )
        )

        activity = self.executor.execute(
            action
        )

        activity.content = actual_content

        return activity

    # ==================================================
    # 4. RESOURCE RECOMMENDATION
    # ==================================================

    def get_resource_recommendations(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        top_k: int = 3,
        candidate_count: int = 10,
    ) -> ResourceRecommendation:
        """
        Retrieve and rank real learning resources using
        the student's CACM state.
        """

        return self.resource_recommender.recommend(
            student=student,
            concept_name=concept_name,
            top_k=top_k,
            candidate_count=candidate_count,
        )

    # ==================================================
    # 5. COMPLETE LEARNING EXPERIENCE
    # ==================================================

    def get_learning_experience(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        include_resources: bool = True,
        top_k: int = 3,
    ) -> LearningExperience:
        """
        Generate personalized activity plus optional
        resource recommendations.
        """

        activity = self.get_next_activity(
            student=student,
            concept_name=concept_name,
        )

        recommendations = None

        if include_resources:

            try:
                recommendations = (
                    self.get_resource_recommendations(
                        student=student,
                        concept_name=concept_name,
                        top_k=top_k,
                    )
                )

            except RuntimeError:
                # External resource APIs must not destroy
                # the core learning experience.
                recommendations = None

        return LearningExperience(
            activity=activity,
            recommendations=recommendations,
        )

    # ==================================================
    # 6. GENERATE SINGLE PRACTICE QUESTION
    # ==================================================

    def generate_practice_question(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> QuizQuestion:
        """
        Generate one standalone practice question.

        This method is preserved for compatibility.

        For a full adaptive practice experience, use
        start_practice_session().
        """

        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        state = student.get_concept(
            concept_name
        )

        action = self.choose_action(
            student=student,
            concept_name=concept_name,
        )

        difficulty = action.difficulty

        return self.quiz_generator.generate(
            concept_name=concept_name,
            difficulty=difficulty,
            mastery=state.mastery,
            confidence=state.confidence,
            quiz_type="practice_quiz",
        )

    # ==================================================
    # 7. SUBMIT SINGLE PRACTICE ANSWER
    # ==================================================

    def submit_practice_answer(
        self, student, question, answer, *, assessment_id=None,
        generate_next_activity=True,
    ) -> LearningAssessmentOutcome:
        """Persist evaluation and evidence before optional follow-up generation."""
        if not isinstance(student, StudentCognitiveModel):
            raise TypeError("student must be a StudentCognitiveModel.")
        if not isinstance(question, QuizQuestion):
            raise TypeError("question must be a QuizQuestion.")
        answer = answer.strip()
        if not answer:
            raise ValueError("answer cannot be empty.")
        engine = self.cognitive_engine
        request = StudentAnswer(student.user_id, question, answer)
        record = assessment(engine, student, assessment_id or "learning:" + question.question_id, request)
        evaluation = once(engine, record, "evaluation", lambda: self.answer_evaluator.evaluate(request))
        misconceptions = once(engine, record, "misconceptions", lambda:
            self.misconception_analyzer.analyze(request) if evaluation.performance == 0.0 else [])
        evaluation.detected_misconceptions = misconceptions
        def contradicted_targets():
            if not evaluation.is_correct or evaluation.performance < 1.0:
                return []
            state = student.find_concept(question.concept_name)
            hypotheses = state.misconception_hypotheses if state is not None else {}
            return sorted({name for name in question.misconception_targets
                           if name in hypotheses and hypotheses[name].status in ("active", "uncertain")})
        targets = once(engine, record, "contradicted_misconceptions", contradicted_targets)
        evidence = once(engine, record, "evidence", lambda: LearningEvidence(
            user_id=student.user_id, concept_name=question.concept_name, source_agent="learning",
            evidence_type="practice_quiz", performance=evaluation.performance,
            difficulty=self._difficulty_to_score(question.difficulty), reliability=self.PRACTICE_RELIABILITY,
            detected_misconceptions=misconceptions, evidence_id=record["assessment_id"]))
        cognitive = once(engine, record, "cognitive_result", lambda: engine.process_evidence(
            student, evidence, contradicted_misconceptions=targets))
        outcome = once(engine, record, "assessment", lambda: LearningAssessmentOutcome(
            question, request, evaluation, evidence, cognitive, None))
        if generate_next_activity:
            outcome.next_activity = once(engine, record, "next_activity", lambda:
                self.get_next_activity(student, question.concept_name))
            persist(engine)
        return outcome

    # ==================================================
    # 8. START ADAPTIVE PRACTICE SESSION
    # ==================================================

    def start_practice_session(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        learning_context: str | None = None,
        max_questions: int = 3,
    ) -> PracticeSessionStart:
        """
        Start a sequential adaptive practice session.

        The first question is generated from the current
        CACM state.

        Later questions are NOT generated yet.
        They are generated only after previous answers
        have been evaluated and CACM has been updated.
        """

        if not isinstance(
            student,
            StudentCognitiveModel,
        ):
            raise TypeError(
                "student must be a StudentCognitiveModel."
            )

        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        session = PracticeSession(
            user_id=student.user_id,
            concept_name=concept_name,
            learning_context=learning_context,
            max_questions=max_questions,
        )

        decision = (
            self.practice_policy.decide_next_question(
                student=student,
                session=session,
            )
        )

        question = (
            self._generate_session_question(
                student=student,
                session=session,
                decision=decision,
            )
        )

        session.set_current_question(
            question
        )

        return PracticeSessionStart(
            session=session,
            question=question,
            decision=decision,
        )

    # ==================================================
    # 9. SUBMIT ADAPTIVE SESSION ANSWER
    # ==================================================

    def submit_practice_session_answer(
        self, student, session, answer, *, question_id=None,
    ) -> PracticeSessionOutcome:
        """A saved question ID binds retries to the answer that was actually assessed."""
        self._validate_session_student(student, session)
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("answer cannot be empty.")
        engine = self.cognitive_engine
        with lock_for(engine):
            if question_id is None and session.pending_assessment_id:
                existing = engine.assessment_records.get((student.user_id, session.pending_assessment_id))
                if existing:
                    question_id = existing["request"].question.question_id
            question_id = question_id or (session.current_question.question_id if session.current_question else None)
            if question_id is None:
                raise ValueError("Practice session has no active question.")
            identity = "learning:" + session.session_id + ":" + question_id
            existing = engine.assessment_records.get((student.user_id, identity))
            if existing is not None:
                question = existing["request"].question
            else:
                if session.is_complete:
                    raise ValueError("Practice session is already complete.")
                question = session.current_question
                if question is None or question.question_id != question_id:
                    raise ValueError("This answer belongs to a different practice question.")
            request = StudentAnswer(student.user_id, question, answer.strip())
            record = assessment(engine, student, identity, request)
            if "outcome" in record["stages"]:
                return record["stages"]["outcome"]
            session.pending_assessment_id = identity
            persist(engine)
            assessed = self.submit_practice_answer(student, question, answer,
                assessment_id=identity, generate_next_activity=False)

            def record_attempt():
                if not any(a.question.question_id == question_id for a in session.attempts):
                    if session.current_question is None or session.current_question.question_id != question_id:
                        raise ValueError("The active question changed before its answer was recorded.")
                    session.record_attempt(answer, assessed.evaluation)
                return True
            once(engine, record, "attempt_recorded", record_attempt)
            assessed.next_activity = once(engine, record, "next_activity", lambda:
                self.get_next_activity(student, question.concept_name))
            if session.is_complete:
                summary = once(engine, record, "summary", lambda:
                    self.get_practice_session_summary(student, session, assessed.next_activity))
                outcome = once(engine, record, "outcome", lambda:
                    PracticeSessionOutcome(session, assessed, summary=summary))
            else:
                decision = once(engine, record, "next_decision", lambda:
                    self.practice_policy.decide_next_question(student=student, session=session))
                next_question = once(engine, record, "next_question", lambda:
                    self._generate_session_question(student=student, session=session, decision=decision))
                session.set_current_question(next_question)
                outcome = once(engine, record, "outcome", lambda:
                    PracticeSessionOutcome(session, assessed, next_question, decision))
            session.pending_assessment_id = None
            persist(engine)
            return outcome

    def resume_practice_session(self, student, session):
        self._validate_session_student(student, session)
        record = self.cognitive_engine.assessment_records.get((student.user_id, session.pending_assessment_id))
        if record is None:
            raise ValueError("No saved practice submission is available to resume.")
        request = record["request"]
        return self.submit_practice_session_answer(student, session, request.answer,
            question_id=request.question.question_id)

    # ==================================================
    # 10. PRACTICE SESSION SUMMARY
    # ==================================================

    def get_practice_session_summary(
        self,
        student: StudentCognitiveModel,
        session: PracticeSession,
        next_activity: LearningActivity | None = None,
    ) -> PracticeSessionSummary:
        """
        Build the final summary from actual session
        interactions and the final CACM state.

        Average practice performance is reported only as
        a session statistic. It does NOT replace mastery.
        """

        self._validate_session_student(
            student=student,
            session=session,
        )

        if not session.attempts:
            raise ValueError(
                "Cannot summarize an empty practice session."
            )

        correct_answers = 0
        partial_answers = 0
        incorrect_answers = 0

        misconception_hypotheses = []

        for attempt in session.attempts:

            performance = (
                attempt.evaluation.performance
            )

            if performance >= 1.0:
                correct_answers += 1

            elif performance <= 0.0:
                incorrect_answers += 1

            else:
                partial_answers += 1

            for misconception in (
                attempt.evaluation
                .detected_misconceptions
            ):
                cleaned = misconception.strip()

                if (
                    cleaned
                    and cleaned
                    not in misconception_hypotheses
                ):
                    misconception_hypotheses.append(
                        cleaned
                    )

        state = student.get_concept(
            session.concept_name
        )

        if next_activity is None:
            next_activity = self.get_next_activity(
                student=student,
                concept_name=session.concept_name,
            )

        return PracticeSessionSummary(
            concept_name=session.concept_name,
            questions_completed=(
                session.questions_completed
            ),
            correct_answers=correct_answers,
            partial_answers=partial_answers,
            incorrect_answers=incorrect_answers,
            average_performance=(
                session.average_performance()
            ),
            final_mastery=state.mastery,
            final_confidence=state.confidence,
            misconception_hypotheses=(
                misconception_hypotheses
            ),
            next_activity=next_activity,
        )

    # ==================================================
    # 11. GENERIC PERFORMANCE SUBMISSION
    # ==================================================

    def submit_performance(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        performance: float,
        evidence_type: str,
        difficulty: float,
        reliability: float,
        detected_misconceptions=None,
    ):
        """
        Convert already-evaluated student performance
        into LearningEvidence.

        Students do not manually enter these values in
        the final application.
        """

        if detected_misconceptions is None:
            detected_misconceptions = []

        evidence = LearningEvidence(
            user_id=student.user_id,
            concept_name=concept_name,
            source_agent="learning",
            evidence_type=evidence_type,
            performance=performance,
            difficulty=difficulty,
            reliability=reliability,
            detected_misconceptions=(
                detected_misconceptions
            ),
        )

        return self.cognitive_engine.process_evidence(
            student=student,
            evidence=evidence,
        )

    # ==================================================
    # 12. GENERIC UPDATE -> RE-PLAN
    # ==================================================

    def submit_and_replan(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        performance: float,
        evidence_type: str,
        difficulty: float,
        reliability: float,
        detected_misconceptions=None,
    ):
        """
        Generic evidence submission followed by
        automatic Learning Agent re-planning.
        """

        cognitive_result = self.submit_performance(
            student=student,
            concept_name=concept_name,
            performance=performance,
            evidence_type=evidence_type,
            difficulty=difficulty,
            reliability=reliability,
            detected_misconceptions=(
                detected_misconceptions
            ),
        )

        next_activity = self.get_next_activity(
            student=student,
            concept_name=concept_name,
        )

        return {
            "cognitive_result": cognitive_result,
            "next_activity": next_activity,
        }

    # ==================================================
    # INTERNAL: GENERATE SESSION QUESTION
    # ==================================================

    def _generate_session_question(
        self,
        student: StudentCognitiveModel,
        session: PracticeSession,
        decision: PracticeDecision,
    ) -> QuizQuestion:
        """
        Generate one question using:

        - updated CACM state
        - Learning Agent practice decision
        - previous session history
        - targeted misconception hypotheses
        - learning context

        Gemini executes the generation request but does
        not make the pedagogical decision.
        """

        state = student.get_concept(
            session.concept_name
        )

        history = (
            session.get_question_history()
        )

        question = self.quiz_generator.generate(
            concept_name=session.concept_name,
            difficulty=decision.difficulty,
            mastery=state.mastery,
            confidence=state.confidence,
            quiz_type="practice_quiz",
            previous_questions=history,
            target_misconceptions=(
                decision.target_misconceptions
            ),
            learning_context=(
                session.learning_context
            ),
        )
        # Generated labels cannot introduce arbitrary contradiction targets.
        question.misconception_targets = [name for name in question.misconception_targets
                                         if name in decision.target_misconceptions]
        return question

    def get_study_plan(self, student, goal_topic, *, now=None):
        from app.learning_agent.study_planner import LearningStudyPlanner
        return LearningStudyPlanner().create_plan(student, self.cognitive_engine, goal_topic, now=now)

    def get_planned_learning_experience(self, student, step):
        """Execute a current plan step using the existing providers and ranking."""
        from app.learning_agent.study_planner import LearningStudyPlanner
        from app.learning_agent.agent import LearningAction
        planner = LearningStudyPlanner()
        current = planner.describe(student, self.cognitive_engine, step.topic_name,
                                   revision=step.purpose == "revise")
        if current.purpose == "diagnostic":
            raise ValueError("Resolve the conflict through the learning diagnostic first.")
        topic = planner.bank.get(current.topic_name)
        assessed = student.find_concept(current.topic_name)
        reviewing = assessed is not None and assessed.attempts > 0 and current.purpose in ("remediate", "verify", "revise")
        if not reviewing and topic and any(not planner.ready(student, self.cognitive_engine, p) for p in topic.prerequisites):
            raise ValueError("Complete the recommended prerequisites before this planned step.")
        action_type = {"learn": "teach_concept", "remediate": "teach_concept",
                       "practice": "practice_quiz", "verify": "verification_quiz",
                       "revise": "verification_quiz", "extend": "advance_topic"}[current.purpose]
        action = LearningAction(action_type, current.topic_name, current.difficulty, current.reason)
        request = self.content_generator.generate(student=student, action=action)
        content = self.content_provider.create_content(request)
        activity = self.executor.execute(action)
        activity.content = content
        try:
            resources = self.get_resource_recommendations(student, current.topic_name, top_k=10)
        except RuntimeError:
            resources = None
        return LearningExperience(activity, resources)

    # ==================================================
    # INTERNAL: SESSION VALIDATION
    # ==================================================

    @staticmethod
    def _validate_session_student(
        student: StudentCognitiveModel,
        session: PracticeSession,
    ) -> None:
        """
        Ensure a practice session cannot accidentally be
        submitted against another student's cognitive
        model.
        """

        if not isinstance(
            student,
            StudentCognitiveModel,
        ):
            raise TypeError(
                "student must be a StudentCognitiveModel."
            )

        if not isinstance(
            session,
            PracticeSession,
        ):
            raise TypeError(
                "session must be a PracticeSession."
            )

        if student.user_id != session.user_id:
            raise ValueError(
                "Practice session belongs to a different "
                "student."
            )

    # ==================================================
    # INTERNAL: DIFFICULTY SCORE
    # ==================================================

    @classmethod
    def _difficulty_to_score(
        cls,
        difficulty: str,
    ) -> float:
        """
        Convert categorical question difficulty into the
        numeric value expected by LearningEvidence.

        Current prototype mapping:

        easy   -> 0.30
        medium -> 0.60
        hard   -> 0.85
        """

        difficulty = (
            difficulty.strip().lower()
        )

        if difficulty not in cls.DIFFICULTY_SCORE:
            raise ValueError(
                "Unsupported question difficulty: "
                f"{difficulty}"
            )

        return cls.DIFFICULTY_SCORE[
            difficulty
        ]
