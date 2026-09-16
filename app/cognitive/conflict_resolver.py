from dataclasses import dataclass

from app.cognitive.evidence import LearningEvidence
from app.cognitive.conflict_detector import CognitiveConflict


@dataclass
class ConflictResolution:
    """
    Result produced after evaluating diagnostic evidence
    against an existing cross-agent cognitive conflict.
    """

    concept_name: str

    resolved: bool

    supported_agent: str

    diagnostic_performance: float

    first_distance: float

    second_distance: float

    reason: str


class ConflictResolver:
    """
    Resolves cross-agent cognitive conflicts using
    diagnostic evidence.

    Instead of automatically trusting a diagnostic result,
    the resolver checks how strongly that result supports
    either side of the disagreement.
    """

    def __init__(
        self,
        minimum_reliability: float = 0.70,
        minimum_difficulty: float = 0.50,
        support_margin: float = 0.15,
    ):

        self.minimum_reliability = minimum_reliability
        self.minimum_difficulty = minimum_difficulty
        self.support_margin = support_margin


    def resolve(
        self,
        conflict: CognitiveConflict,
        diagnostic_evidence: LearningEvidence,
    ) -> ConflictResolution:

        # --------------------------------------------------
        # 1. Check that the diagnostic is for
        #    the same concept
        # --------------------------------------------------

        if (
            conflict.concept_name.lower()
            != diagnostic_evidence.concept_name.lower()
        ):

            return ConflictResolution(
                concept_name=conflict.concept_name,
                resolved=False,
                supported_agent="uncertain",
                diagnostic_performance=(
                    diagnostic_evidence.performance
                ),
                first_distance=0.0,
                second_distance=0.0,
                reason=(
                    "Diagnostic evidence belongs to a "
                    "different concept."
                ),
            )


        # --------------------------------------------------
        # 2. Check evidence type
        # --------------------------------------------------

        if (
            diagnostic_evidence.evidence_type
            != "diagnostic_quiz"
        ):

            return ConflictResolution(
                concept_name=conflict.concept_name,
                resolved=False,
                supported_agent="uncertain",
                diagnostic_performance=(
                    diagnostic_evidence.performance
                ),
                first_distance=0.0,
                second_distance=0.0,
                reason=(
                    "Evidence is not a diagnostic quiz."
                ),
            )


        # --------------------------------------------------
        # 3. Check diagnostic reliability
        # --------------------------------------------------

        if (
            diagnostic_evidence.reliability
            < self.minimum_reliability
        ):

            return ConflictResolution(
                concept_name=conflict.concept_name,
                resolved=False,
                supported_agent="uncertain",
                diagnostic_performance=(
                    diagnostic_evidence.performance
                ),
                first_distance=0.0,
                second_distance=0.0,
                reason=(
                    "Diagnostic evidence reliability "
                    "is too low."
                ),
            )


        # --------------------------------------------------
        # 4. Check diagnostic difficulty
        # --------------------------------------------------

        if (
            diagnostic_evidence.difficulty
            < self.minimum_difficulty
        ):

            return ConflictResolution(
                concept_name=conflict.concept_name,
                resolved=False,
                supported_agent="uncertain",
                diagnostic_performance=(
                    diagnostic_evidence.performance
                ),
                first_distance=0.0,
                second_distance=0.0,
                reason=(
                    "Diagnostic assessment is not "
                    "sufficiently informative."
                ),
            )


        # --------------------------------------------------
        # 5. Measure distance from both conflicting
        #    pieces of evidence
        # --------------------------------------------------

        first_distance = abs(
            diagnostic_evidence.performance
            - conflict.first_performance
        )

        second_distance = abs(
            diagnostic_evidence.performance
            - conflict.second_performance
        )


        # --------------------------------------------------
        # 6. Determine which agent is better supported
        # --------------------------------------------------

        distance_difference = abs(
            first_distance - second_distance
        )


        # Diagnostic sits too close to the middle.
        # It cannot clearly resolve the disagreement.

        if distance_difference < self.support_margin:

            return ConflictResolution(
                concept_name=conflict.concept_name,
                resolved=False,
                supported_agent="uncertain",
                diagnostic_performance=(
                    diagnostic_evidence.performance
                ),
                first_distance=round(
                    first_distance,
                    3
                ),
                second_distance=round(
                    second_distance,
                    3
                ),
                reason=(
                    "Diagnostic evidence does not clearly "
                    "support either agent."
                ),
            )


        # --------------------------------------------------
        # 7. Diagnostic supports first agent
        # --------------------------------------------------

        if first_distance < second_distance:

            supported_agent = conflict.first_agent

        else:

            supported_agent = conflict.second_agent


        # --------------------------------------------------
        # 8. Conflict successfully resolved
        # --------------------------------------------------

        return ConflictResolution(
            concept_name=conflict.concept_name,
            resolved=True,
            supported_agent=supported_agent,
            diagnostic_performance=(
                diagnostic_evidence.performance
            ),
            first_distance=round(
                first_distance,
                3
            ),
            second_distance=round(
                second_distance,
                3
            ),
            reason=(
                "Diagnostic evidence clearly supports "
                f"the {supported_agent} agent."
            ),
        )