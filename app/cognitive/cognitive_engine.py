from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.evidence_store import EvidenceStore
from app.cognitive.mastery_engine import MasteryEngine
from app.cognitive.conflict_detector import ConflictDetector
from app.cognitive.conflict_resolver import ConflictResolver
from app.cognitive.misconception_manager import (
    CognitiveMisconceptionManager,
)


class CognitiveEngine:
    """
    Central cognitive engine for the shared student model.

    Responsibilities:
    1. Receive evidence from Learning, Research and Coding agents.
    2. Store the evidence.
    3. Update concept mastery.
    4. Detect cross-agent cognitive conflicts.
    5. Resolve conflicts using diagnostic evidence.
    6. Create and update misconception hypotheses.
    """

    def __init__(self):
        self.evidence_store = EvidenceStore()
        self.mastery_engine = MasteryEngine()
        self.conflict_detector = ConflictDetector()
        self.conflict_resolver = ConflictResolver()

        self.misconception_manager = (
            CognitiveMisconceptionManager()
        )

        # Key:
        # (user_id, concept_name)
        #
        # Value:
        # list of currently unresolved conflicts
        self.active_conflicts = {}


    # ==================================================
    # PROCESS EVIDENCE
    # ==================================================

    def process_evidence(
        self,
        student: StudentCognitiveModel,
        evidence: LearningEvidence,
    ):
        """
        Process one new piece of cognitive evidence.

        Evidence may come from:
        - Learning Agent
        - Research Agent
        - Coding Agent
        """

        # ------------------------------------------------
        # STEP 1: VALIDATE USER
        # ------------------------------------------------

        if student.user_id != evidence.user_id:
            raise ValueError(
                "Evidence user_id does not match "
                "student user_id."
            )


        # ------------------------------------------------
        # STEP 2: GET PREVIOUS EVIDENCE
        # ------------------------------------------------
        #
        # IMPORTANT:
        # We retrieve previous evidence BEFORE storing
        # the new evidence.
        #
        # Otherwise, the new evidence could be compared
        # with itself during conflict detection.
        # ------------------------------------------------

        previous_evidence = (
            self.evidence_store
            .get_evidence_for_concept(
                user_id=evidence.user_id,
                concept_name=evidence.concept_name,
            )
        )


        # ------------------------------------------------
        # STEP 3: DETECT CROSS-AGENT CONFLICTS
        # ------------------------------------------------

        new_conflicts = []

        for previous in previous_evidence:

            conflict = (
                self.conflict_detector.detect(
                    previous,
                    evidence,
                )
            )

            if conflict is not None:
                new_conflicts.append(
                    conflict
                )


        # ------------------------------------------------
        # STEP 4: STORE NEW EVIDENCE
        # ------------------------------------------------

        self.evidence_store.add_evidence(
            evidence
        )


        # ------------------------------------------------
        # STEP 5: UPDATE MASTERY
        # ------------------------------------------------

        updated_concept = (
            self.mastery_engine
            .update_from_evidence(
                student=student,
                evidence=evidence,
            )
        )


        # ------------------------------------------------
        # STEP 6: UPDATE MISCONCEPTION HYPOTHESES
        # ------------------------------------------------
        #
        # Every detected misconception is treated as
        # SUPPORTING evidence for that hypothesis.
        #
        # First observation:
        #     create hypothesis
        #
        # Repeated observation:
        #     strengthen hypothesis
        #
        # Because the source agent is stored, later
        # Learning, Research and Coding agents can all
        # contribute to the same misconception state.
        # ------------------------------------------------

        updated_hypotheses = []

        for misconception in (
            evidence.detected_misconceptions
        ):

            hypothesis = (
                self.misconception_manager
                .record_support(
                    student=student,
                    concept_name=evidence.concept_name,
                    description=misconception,
                    source_agent=evidence.source_agent,
                )
            )

            updated_hypotheses.append(
                hypothesis
            )


        # ------------------------------------------------
        # STEP 7: BUILD CONFLICT KEY
        # ------------------------------------------------

        key = (
            evidence.user_id,
            evidence.concept_name,
        )


        # ------------------------------------------------
        # STEP 8: STORE NEW CONFLICTS
        # ------------------------------------------------
        #
        # Diagnostic evidence is used for resolving
        # existing conflicts.
        #
        # Therefore we do not add conflicts generated
        # by diagnostic evidence as new active conflicts.
        # ------------------------------------------------

        if (
            evidence.evidence_type
            != "diagnostic_quiz"
        ):

            if new_conflicts:

                if key not in self.active_conflicts:
                    self.active_conflicts[
                        key
                    ] = []

                self.active_conflicts[
                    key
                ].extend(
                    new_conflicts
                )


        # ------------------------------------------------
        # STEP 9: RESOLVE ACTIVE CONFLICTS
        # ------------------------------------------------

        resolution_results = []

        if (
            evidence.evidence_type
            == "diagnostic_quiz"
            and key in self.active_conflicts
        ):

            remaining_conflicts = []

            for conflict in (
                self.active_conflicts[key]
            ):

                resolution = (
                    self.conflict_resolver.resolve(
                        conflict=conflict,
                        diagnostic_evidence=evidence,
                    )
                )

                resolution_results.append(
                    resolution
                )

                if not resolution.resolved:
                    remaining_conflicts.append(
                        conflict
                    )


            # If some conflicts could not be resolved,
            # keep only those conflicts.
            if remaining_conflicts:

                self.active_conflicts[
                    key
                ] = remaining_conflicts

            # If every conflict was resolved,
            # remove the key completely.
            else:

                self.active_conflicts.pop(
                    key,
                    None,
                )


        # ------------------------------------------------
        # STEP 10: CONFLICT RESOLUTION SUMMARY
        # ------------------------------------------------

        conflict_resolved = any(
            result.resolved
            for result in resolution_results
        )


        # ------------------------------------------------
        # STEP 11: RETURN RESULT
        # ------------------------------------------------

        return {
    # Updated cognitive state for this concept
    "concept": updated_concept,

    # --------------------------------------------------
    # BACKWARD-COMPATIBILITY KEY
    # --------------------------------------------------
    # Older tests and components use:
    #
    # result["conflicts"]
    #
    # Keep this key so existing code does not break.
    "conflicts": new_conflicts,

    # --------------------------------------------------
    # NEW CLEARER KEY
    # --------------------------------------------------
    # Newer components can use:
    #
    # result["new_conflicts"]
    #
    # Both keys currently refer to the same conflicts.
    "new_conflicts": new_conflicts,

    # Results produced when diagnostic evidence
    # attempts to resolve existing conflicts.
    "resolution_results": resolution_results,

    # True if at least one conflict was resolved
    # during this evidence-processing step.
    "conflict_resolved": conflict_resolved,

    # Whether unresolved conflict still exists
    # after processing this evidence.
    "has_active_conflict": self.has_conflict(
        user_id=evidence.user_id,
        concept_name=evidence.concept_name,
    ),

    # Misconception hypotheses created or updated
    # by this particular evidence item.
    "updated_misconception_hypotheses": (
        updated_hypotheses
    ),
}


    # ==================================================
    # CHECK ACTIVE CONFLICT
    # ==================================================

    def has_conflict(
        self,
        user_id: str,
        concept_name: str,
    ) -> bool:
        """
        Returns True when unresolved cross-agent
        conflicts exist for this concept.
        """

        key = (
            user_id,
            concept_name,
        )

        return bool(
            self.active_conflicts.get(
                key
            )
        )


    # ==================================================
    # GET ACTIVE CONFLICTS
    # ==================================================

    def get_conflicts(
        self,
        user_id: str,
        concept_name: str,
    ):
        """
        Return unresolved conflicts for a concept.
        """

        key = (
            user_id,
            concept_name,
        )

        return self.active_conflicts.get(
            key,
            [],
        )


    # ==================================================
    # MANUALLY CLEAR CONFLICTS
    # ==================================================

    def resolve_conflicts(
        self,
        user_id: str,
        concept_name: str,
    ) -> None:
        """
        Manually remove all active conflicts for
        a student's concept.

        This is mainly a utility method.
        """

        key = (
            user_id,
            concept_name,
        )

        self.active_conflicts.pop(
            key,
            None,
        )


    # ==================================================
    # RECORD MISCONCEPTION CONTRADICTION
    # ==================================================

    def record_misconception_contradiction(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        misconception: str,
        source_agent: str = "learning",
    ):
        """
        Record evidence AGAINST an existing
        misconception hypothesis.

        Example:

        Student previously confused n-2 with n-1.

        A targeted reassessment is generated.

        If the student answers correctly, that result
        provides contradicting evidence against the
        misconception hypothesis.
        """

        return (
            self.misconception_manager
            .record_contradiction(
                student=student,
                concept_name=concept_name,
                description=misconception,
                source_agent=source_agent,
            )
        )


    # ==================================================
    # GET MISCONCEPTION HYPOTHESIS
    # ==================================================

    def get_misconception_hypothesis(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        misconception: str,
    ):
        """
        Retrieve one structured misconception
        hypothesis from the shared cognitive model.
        """

        return (
            self.misconception_manager
            .get_hypothesis(
                student=student,
                concept_name=concept_name,
                description=misconception,
            )
        )