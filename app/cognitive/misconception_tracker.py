from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MisconceptionHypothesis:
    """
    Represents a misconception as a hypothesis.

    Instead of permanently assuming that a student
    has a misconception, we maintain evidence for
    and against the hypothesis.
    """

    description: str

    supporting_evidence: int = 0
    contradicting_evidence: int = 0

    confidence: float = 0.5

    status: str = "active"

    source_agents: list[str] = field(
        default_factory=list
    )

    last_updated: datetime = field(
        default_factory=datetime.now
    )


class MisconceptionTracker:
    """
    Tracks misconception hypotheses using
    supporting and contradicting evidence.

    NOTE:
    The numerical thresholds used here are
    initial engineering heuristics.

    They will later be calibrated and evaluated
    experimentally.
    """

    # How much confidence increases when new
    # evidence supports the misconception.
    SUPPORT_INCREMENT = 0.15

    # How much confidence decreases when evidence
    # contradicts the misconception.
    CONTRADICTION_DECREMENT = 0.20

    # Confidence <= this value means the
    # misconception is considered resolved.
    RESOLUTION_THRESHOLD = 0.25

    # Confidence below this value but above the
    # resolution threshold means we are uncertain.
    ACTIVE_THRESHOLD = 0.40


    # ==================================================
    # CREATE NEW HYPOTHESIS
    # ==================================================

    def create_hypothesis(
        self,
        description: str,
        source_agent: str,
    ) -> MisconceptionHypothesis:
        """
        Creates a new misconception hypothesis.

        A newly detected misconception begins with
        one piece of supporting evidence and an
        initial confidence of 0.60.
        """

        description = description.strip()
        source_agent = source_agent.strip().lower()

        if not description:
            raise ValueError(
                "Misconception description cannot be empty."
            )

        if not source_agent:
            raise ValueError(
                "source_agent cannot be empty."
            )

        hypothesis = MisconceptionHypothesis(
            description=description,

            supporting_evidence=1,

            contradicting_evidence=0,

            confidence=0.60,

            status="active",

            source_agents=[
                source_agent
            ],
        )

        return hypothesis


    # ==================================================
    # ADD SUPPORTING EVIDENCE
    # ==================================================

    def add_support(
        self,
        hypothesis: MisconceptionHypothesis,
        source_agent: str,
    ) -> MisconceptionHypothesis:
        """
        Called when new evidence supports the
        misconception hypothesis.

        Example:
        The student makes the same conceptual
        mistake again in a reassessment.
        """

        hypothesis.supporting_evidence += 1

        hypothesis.confidence = round(
            min(
                1.0,
                hypothesis.confidence
                + self.SUPPORT_INCREMENT
            ),
            3,
        )

        self._add_source(
            hypothesis=hypothesis,
            source_agent=source_agent,
        )

        self._update_status(
            hypothesis
        )

        hypothesis.last_updated = (
            datetime.now()
        )

        return hypothesis


    # ==================================================
    # ADD CONTRADICTING EVIDENCE
    # ==================================================

    def add_contradiction(
        self,
        hypothesis: MisconceptionHypothesis,
        source_agent: str,
    ) -> MisconceptionHypothesis:
        """
        Called when new evidence contradicts the
        misconception hypothesis.

        Example:
        The student correctly answers a question
        specifically designed to reassess the
        misconception.
        """

        hypothesis.contradicting_evidence += 1

        hypothesis.confidence = round(
            max(
                0.0,
                hypothesis.confidence
                - self.CONTRADICTION_DECREMENT
            ),
            3,
        )

        self._add_source(
            hypothesis=hypothesis,
            source_agent=source_agent,
        )

        self._update_status(
            hypothesis
        )

        hypothesis.last_updated = (
            datetime.now()
        )

        return hypothesis


    # ==================================================
    # UPDATE STATUS
    # ==================================================

    def _update_status(
        self,
        hypothesis: MisconceptionHypothesis,
    ) -> None:
        """
        Converts misconception confidence into
        one of three states:

        active
        uncertain
        resolved
        """

        confidence = round(
            hypothesis.confidence,
            3,
        )

        if (
            confidence
            <= self.RESOLUTION_THRESHOLD
        ):

            hypothesis.status = "resolved"

        elif (
            confidence
            < self.ACTIVE_THRESHOLD
        ):

            hypothesis.status = "uncertain"

        else:

            hypothesis.status = "active"


    # ==================================================
    # ADD SOURCE AGENT
    # ==================================================

    def _add_source(
        self,
        hypothesis: MisconceptionHypothesis,
        source_agent: str,
    ) -> None:
        """
        Records which agents have contributed
        evidence to the misconception hypothesis.

        Later this allows evidence to come from:

        Learning Agent
        Research Agent
        Coding Agent
        """

        source_agent = (
            source_agent.strip().lower()
        )

        if (
            source_agent
            and source_agent
            not in hypothesis.source_agents
        ):

            hypothesis.source_agents.append(
                source_agent
            )