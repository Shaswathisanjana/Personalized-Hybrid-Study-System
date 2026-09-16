from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.evidence_store import EvidenceStore
from app.cognitive.mastery_engine import MasteryEngine
from app.cognitive.conflict_detector import ConflictDetector
from app.cognitive.conflict_resolver import ConflictResolver


class CognitiveEngine:
    """
    Central cognitive processing layer shared by all agents.

    Responsibilities:
    1. Store cross-agent evidence
    2. Update concept mastery
    3. Detect cognitive conflicts
    4. Maintain active conflicts
    5. Resolve conflicts using diagnostic evidence
    """

    def __init__(self):

        self.evidence_store = EvidenceStore()
        self.mastery_engine = MasteryEngine()
        self.conflict_detector = ConflictDetector()
        self.conflict_resolver = ConflictResolver()

        # (user_id, concept_name) -> list of conflicts
        self.active_conflicts = {}


    # ==================================================
    # PROCESS EVIDENCE
    # ==================================================

    def process_evidence(
        self,
        student: StudentCognitiveModel,
        evidence: LearningEvidence,
    ):

        # --------------------------------------------------
        # STEP 1: Validate student
        # --------------------------------------------------

        if student.user_id != evidence.user_id:
            raise ValueError(
                "Evidence belongs to a different student."
            )


        # --------------------------------------------------
        # STEP 2: Get previous evidence
        # --------------------------------------------------

        previous_evidence = (
            self.evidence_store.get_evidence_for_concept(
                user_id=evidence.user_id,
                concept_name=evidence.concept_name,
            )
        )


        # --------------------------------------------------
        # STEP 3: Detect new cross-agent conflicts
        # --------------------------------------------------

        new_conflicts = []

        for old_evidence in previous_evidence:

            # Compare evidence only across different agents
            if (
                old_evidence.source_agent
                == evidence.source_agent
            ):
                continue

            conflict = self.conflict_detector.detect(
                old_evidence,
                evidence,
            )

            if conflict is not None:
                new_conflicts.append(conflict)


        # --------------------------------------------------
        # STEP 4: Store evidence
        # --------------------------------------------------

        self.evidence_store.add_evidence(
            evidence
        )


        # --------------------------------------------------
        # STEP 5: Update mastery
        # --------------------------------------------------

        updated_concept = (
            self.mastery_engine.update_from_evidence(
                student=student,
                evidence=evidence,
            )
        )


        # --------------------------------------------------
        # STEP 6: Get conflict key
        # --------------------------------------------------

        key = (
            evidence.user_id,
            evidence.concept_name.lower(),
        )


        # --------------------------------------------------
        # STEP 7: Store newly detected conflicts
        #
        # Diagnostic evidence is used for RESOLUTION,
        # so we do not store conflicts created by the
        # diagnostic itself as new active conflicts.
        # --------------------------------------------------

        if (
            new_conflicts
            and evidence.evidence_type != "diagnostic_quiz"
        ):

            self.active_conflicts.setdefault(
                key,
                []
            ).extend(
                new_conflicts
            )


        # --------------------------------------------------
        # STEP 8: Try to resolve existing conflicts
        # --------------------------------------------------

        resolution_results = []

        if (
            evidence.evidence_type == "diagnostic_quiz"
            and self.has_conflict(
                evidence.user_id,
                evidence.concept_name,
            )
        ):

            current_conflicts = self.get_conflicts(
                evidence.user_id,
                evidence.concept_name,
            )

            unresolved_conflicts = []

            for conflict in current_conflicts:

                resolution = (
                    self.conflict_resolver.resolve(
                        conflict,
                        evidence,
                    )
                )

                resolution_results.append(
                    resolution
                )

                # If the diagnostic was not strong enough
                # to resolve this conflict, keep it active.
                if not resolution.resolved:
                    unresolved_conflicts.append(
                        conflict
                    )


            # Replace the old conflict list with only
            # unresolved conflicts.
            if unresolved_conflicts:

                self.active_conflicts[key] = (
                    unresolved_conflicts
                )

            else:

                self.active_conflicts.pop(
                    key,
                    None
                )


        # --------------------------------------------------
        # STEP 9: Determine whether anything was resolved
        # --------------------------------------------------

        conflict_resolved = any(
            result.resolved
            for result in resolution_results
        )


        # --------------------------------------------------
        # STEP 10: Return complete result
        # --------------------------------------------------

        return {
            "concept": updated_concept,

            "conflicts": new_conflicts,

            "has_active_conflict": self.has_conflict(
                evidence.user_id,
                evidence.concept_name,
            ),

            "conflict_resolved": conflict_resolved,

            "resolution_results": resolution_results,

            "evidence": evidence,
        }


    # ==================================================
    # CHECK ACTIVE CONFLICT
    # ==================================================

    def has_conflict(
        self,
        user_id: str,
        concept_name: str,
    ) -> bool:

        key = (
            user_id,
            concept_name.lower(),
        )

        return bool(
            self.active_conflicts.get(key)
        )


    # ==================================================
    # GET ACTIVE CONFLICTS
    # ==================================================

    def get_conflicts(
        self,
        user_id: str,
        concept_name: str,
    ):

        key = (
            user_id,
            concept_name.lower(),
        )

        return self.active_conflicts.get(
            key,
            []
        )


    # ==================================================
    # MANUAL CONFLICT CLEARING
    # ==================================================

    def resolve_conflicts(
        self,
        user_id: str,
        concept_name: str,
    ):
        """
        Utility method for explicitly clearing conflicts.

        Normal automatic conflict resolution should happen
        through diagnostic evidence and ConflictResolver.
        """

        key = (
            user_id,
            concept_name.lower(),
        )

        self.active_conflicts.pop(
            key,
            None
        )