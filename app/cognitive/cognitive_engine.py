from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.evidence_store import EvidenceStore
from app.cognitive.mastery_engine import MasteryEngine
from app.cognitive.conflict_detector import ConflictDetector


class CognitiveEngine:
    """
    Central cognitive processing layer.

    All specialized agents send their learning evidence
    to this engine.

    The engine:
    1. Checks previous evidence
    2. Detects cross-agent conflicts
    3. Stores the new evidence
    4. Updates student mastery
    5. Returns the updated cognitive state
    """

    def __init__(self):
        self.evidence_store = EvidenceStore()
        self.mastery_engine = MasteryEngine()
        self.conflict_detector = ConflictDetector()

    def process_evidence(
        self,
        student: StudentCognitiveModel,
        evidence: LearningEvidence,
    ):
        """
        Process one new piece of evidence produced by an agent.
        """

        # --------------------------------------------------
        # STEP 1: Validate student
        # --------------------------------------------------

        if student.user_id != evidence.user_id:
            raise ValueError(
                "Evidence belongs to a different student."
            )

        # --------------------------------------------------
        # STEP 2: Find previous evidence for this concept
        # --------------------------------------------------

        previous_evidence = (
            self.evidence_store.get_evidence_for_concept(
                user_id=evidence.user_id,
                concept_name=evidence.concept_name
            )
        )

        # --------------------------------------------------
        # STEP 3: Detect cross-agent conflicts
        # --------------------------------------------------

        conflicts = []

        for old_evidence in previous_evidence:

            # We only care about disagreement
            # between different agents.
            if (
                old_evidence.source_agent
                == evidence.source_agent
            ):
                continue

            conflict = self.conflict_detector.detect(
                old_evidence,
                evidence
            )

            if conflict is not None:
                conflicts.append(conflict)

        # --------------------------------------------------
        # STEP 4: Store new evidence
        # --------------------------------------------------

        self.evidence_store.add_evidence(evidence)

        # --------------------------------------------------
        # STEP 5: Update mastery
        # --------------------------------------------------

        updated_concept = (
            self.mastery_engine.update_from_evidence(
                student=student,
                evidence=evidence
            )
        )

        # --------------------------------------------------
        # STEP 6: Return processing result
        # --------------------------------------------------

        return {
            "concept": updated_concept,
            "conflicts": conflicts,
            "evidence": evidence
        }