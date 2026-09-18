from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.practice_session import PracticeSession


@dataclass
class PracticeDecision:
    """
    Decision made by the Learning Agent for the next
    question inside an adaptive practice session.

    This decision is made BEFORE Gemini generates the
    actual question.
    """

    difficulty: str

    target_misconceptions: list[str]

    reason: str


class AdaptivePracticePolicy:
    """
    Controls progression inside a short adaptive
    practice session.

    IMPORTANT:

    Gemini does NOT decide question difficulty.

    This policy observes:
    - CACM cognitive state
    - previous practice performance
    - misconception hypotheses from the session

    and decides what the next question should target.

    The policy is intentionally deterministic so that
    its behavior can be inspected and evaluated.
    """

    LEVELS = [
        "easy",
        "medium",
        "hard",
    ]

    # =====================================================
    # PUBLIC DECISION METHOD
    # =====================================================

    def decide_next_question(
        self,
        student: StudentCognitiveModel,
        session: PracticeSession,
    ) -> PracticeDecision:
        """
        Decide the difficulty and misconception target
        for the next practice question.

        Gemini will later generate a question that follows
        this decision.
        """

        if session.is_complete:
            raise ValueError(
                "Practice session is already complete."
            )

        state = student.get_concept(
            session.concept_name
        )

        # -------------------------------------------------
        # FIRST QUESTION
        # -------------------------------------------------
        #
        # There is no practice-session evidence yet.
        #
        # Therefore begin from the current CACM state.
        # -------------------------------------------------

        if not session.attempts:

            difficulty = (
                self._difficulty_from_cognitive_state(
                    mastery=state.mastery,
                    confidence=state.confidence,
                    attempts=state.attempts,
                )
            )

            return PracticeDecision(
                difficulty=difficulty,
                target_misconceptions=[],
                reason=(
                    "Initial practice difficulty selected "
                    "from the current CACM cognitive state."
                ),
            )

        # -------------------------------------------------
        # OBSERVE MOST RECENT PERFORMANCE
        # -------------------------------------------------

        latest_attempt = session.attempts[-1]

        latest_performance = (
            latest_attempt.evaluation.performance
        )

        latest_difficulty = (
            latest_attempt.question.difficulty
        )

        # -------------------------------------------------
        # COLLECT MISCONCEPTION HYPOTHESES
        # -------------------------------------------------

        misconception_candidates = (
            session
            .get_unresolved_misconception_candidates()
        )

        # -------------------------------------------------
        # CLEARLY INCORRECT ANSWER
        # -------------------------------------------------
        #
        # Do not increase difficulty.
        #
        # If a misconception hypothesis exists, target it
        # using a different representation/question.
        # -------------------------------------------------

        if latest_performance == 0.0:

            return PracticeDecision(
                difficulty=latest_difficulty,
                target_misconceptions=(
                    misconception_candidates
                ),
                reason=(
                    "The previous answer was incorrect. "
                    "Maintain difficulty and probe the "
                    "observed weakness before progressing."
                ),
            )

        # -------------------------------------------------
        # PARTIALLY CORRECT ANSWER
        # -------------------------------------------------
        #
        # Keep difficulty stable.
        #
        # We need more evidence before increasing
        # complexity.
        # -------------------------------------------------

        if 0.0 < latest_performance < 1.0:

            return PracticeDecision(
                difficulty=latest_difficulty,
                target_misconceptions=[],
                reason=(
                    "The previous answer was partially "
                    "correct. Maintain difficulty to "
                    "collect stronger evidence."
                ),
            )

        # -------------------------------------------------
        # CORRECT ANSWER
        # -------------------------------------------------
        #
        # A correct answer allows progression, but only
        # by ONE difficulty level.
        #
        # This prevents sudden jumps from easy to hard
        # caused by a single piece of evidence.
        # -------------------------------------------------

        if latest_performance >= 1.0:

            next_difficulty = self._increase_one_level(
                latest_difficulty
            )

            # CACM still acts as a guardrail.
            #
            # If mastery remains very low, we do not
            # escalate merely because one question was
            # answered correctly.

            if state.mastery < 0.40:
                next_difficulty = latest_difficulty

            return PracticeDecision(
                difficulty=next_difficulty,
                target_misconceptions=[],
                reason=(
                    "The previous answer was correct. "
                    "Progress by at most one difficulty "
                    "level while respecting the updated "
                    "CACM mastery estimate."
                ),
            )

        # Defensive fallback.

        return PracticeDecision(
            difficulty=latest_difficulty,
            target_misconceptions=[],
            reason=(
                "Difficulty maintained because no stronger "
                "adaptive rule was applicable."
            ),
        )

    # =====================================================
    # INITIAL DIFFICULTY
    # =====================================================

    def _difficulty_from_cognitive_state(
        self,
        mastery: float,
        confidence: float,
        attempts: int,
    ) -> str:
        """
        Select the initial practice level from CACM.

        Unknown students start easy because the neutral
        mastery prior must not be interpreted as evidence
        of moderate knowledge.
        """

        if attempts == 0:
            return "easy"

        if mastery < 0.40:
            return "easy"

        if mastery < 0.70:
            return "medium"

        if confidence < 0.50:
            return "medium"

        return "hard"

    # =====================================================
    # CONTROLLED DIFFICULTY PROGRESSION
    # =====================================================

    def _increase_one_level(
        self,
        difficulty: str,
    ) -> str:
        """
        Increase difficulty by at most one level.

        easy   -> medium
        medium -> hard
        hard   -> hard
        """

        difficulty = difficulty.strip().lower()

        if difficulty not in self.LEVELS:
            raise ValueError(
                "Unsupported practice difficulty: "
                f"{difficulty}"
            )

        index = self.LEVELS.index(
            difficulty
        )

        if index >= len(self.LEVELS) - 1:
            return self.LEVELS[-1]

        return self.LEVELS[index + 1]