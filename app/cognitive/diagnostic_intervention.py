from dataclasses import dataclass

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel

from app.learning_agent.gemini_quiz_generator import (
    GeminiQuizGenerator,
)
from app.learning_agent.answer_evaluator import (
    AnswerEvaluator,
)
from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
    EvaluationResult,
)


@dataclass
class DiagnosticSession:
    """
    Represents a diagnostic activity created because
    conflicting cognitive evidence was detected.
    """

    user_id: str
    concept_name: str
    question: QuizQuestion
    difficulty: str


@dataclass
class DiagnosticOutcome:
    """
    Final result after the student answers a
    diagnostic question.
    """

    evaluation: EvaluationResult
    evidence: LearningEvidence

    conflict_resolved: bool
    has_active_conflict: bool

    resolution_results: list


class DiagnosticIntervention:
    """
    Handles automatic diagnostic intervention when
    the shared cognitive model contains conflicting
    cross-agent evidence.

    Flow:

        Conflict detected
              ↓
        Generate diagnostic question
              ↓
        Student answers
              ↓
        Evaluate answer
              ↓
        Convert result to diagnostic evidence
              ↓
        CognitiveEngine processes evidence
              ↓
        ConflictResolver attempts resolution
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
        quiz_generator=None,
        answer_evaluator=None,
    ):

        self.cognitive_engine = cognitive_engine

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


    # ======================================================
    # START DIAGNOSTIC
    # ======================================================

    def start(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> DiagnosticSession:
        """
        Generate a diagnostic question only when an
        unresolved cognitive conflict exists.
        """

        has_conflict = self.cognitive_engine.has_conflict(
            user_id=student.user_id,
            concept_name=concept_name,
        )

        if not has_conflict:
            raise ValueError(
                "Diagnostic intervention cannot start "
                "because no active cognitive conflict "
                f"exists for concept '{concept_name}'."
            )

        concept = student.get_concept(
            concept_name
        )

        # For now, conflicts use a medium diagnostic.
        #
        # This is an initial heuristic and should later
        # be calibrated through experiments.
        difficulty = "medium"

        question = self.quiz_generator.generate(
            concept_name=concept_name,
            difficulty=difficulty,
            mastery=concept.mastery,
            confidence=concept.confidence,
            quiz_type="diagnostic_quiz",
        )

        return DiagnosticSession(
            user_id=student.user_id,
            concept_name=concept_name,
            question=question,
            difficulty=difficulty,
        )


    # ======================================================
    # SUBMIT DIAGNOSTIC ANSWER
    # ======================================================

    def submit_answer(
        self,
        student: StudentCognitiveModel,
        session: DiagnosticSession,
        answer: str,
    ) -> DiagnosticOutcome:
        """
        Evaluate the student's real answer and feed the
        resulting diagnostic evidence into the shared
        CognitiveEngine.
        """

        if student.user_id != session.user_id:
            raise ValueError(
                "Diagnostic session belongs to a "
                "different student."
            )

        student_answer = StudentAnswer(
            user_id=student.user_id,
            question=session.question,
            answer=answer,
        )

        evaluation = self.answer_evaluator.evaluate(
            student_answer
        )

        # --------------------------------------------------
        # Convert actual diagnostic result into evidence.
        # --------------------------------------------------
        #
        # Unlike our previous test, performance is NOT
        # manually chosen.
        #
        # It comes directly from AnswerEvaluator.
        # --------------------------------------------------

        diagnostic_evidence = LearningEvidence(
            user_id=student.user_id,
            concept_name=session.concept_name,
            source_agent="learning",
            evidence_type="diagnostic_quiz",
            performance=evaluation.performance,

            # Initial diagnostic heuristics.
            # These should later be calibrated/evaluated.
            difficulty=0.70,
            reliability=0.90,

            detected_misconceptions=(
                evaluation.detected_misconceptions
            ),
        )

        processing_result = (
            self.cognitive_engine.process_evidence(
                student=student,
                evidence=diagnostic_evidence,
            )
        )

        return DiagnosticOutcome(
            evaluation=evaluation,
            evidence=diagnostic_evidence,
            conflict_resolved=processing_result[
                "conflict_resolved"
            ],
            has_active_conflict=processing_result[
                "has_active_conflict"
            ],
            resolution_results=processing_result[
                "resolution_results"
            ],
        )