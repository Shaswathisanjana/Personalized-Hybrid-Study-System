from app.cognitive.evidence import LearningEvidence
from app.cognitive.conflict_detector import ConflictDetector


# --------------------------------------------------
# 1. EVIDENCE FROM LEARNING AGENT
# --------------------------------------------------

learning_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="quiz",
    performance=0.90,
    difficulty=0.60,
    reliability=0.70
)


# --------------------------------------------------
# 2. EVIDENCE FROM CODING AGENT
# --------------------------------------------------

coding_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="coding",
    evidence_type="coding_solution",
    performance=0.30,
    difficulty=0.90,
    reliability=0.85
)


# --------------------------------------------------
# 3. CREATE CONFLICT DETECTOR
# --------------------------------------------------

detector = ConflictDetector()


# --------------------------------------------------
# 4. COMPARE EVIDENCE FROM THE TWO AGENTS
# --------------------------------------------------

conflict = detector.detect(
    learning_evidence,
    coding_evidence
)


# --------------------------------------------------
# 5. DISPLAY RESULT
# --------------------------------------------------

print("\n----- CROSS-AGENT CONFLICT CHECK -----")

if conflict is None:

    print("No significant cognitive conflict detected.")

else:

    print("Conflict detected!")
    print("Concept:", conflict.concept_name)

    print(
        "Agents:",
        conflict.first_agent,
        "vs",
        conflict.second_agent
    )

    print(
        "Performances:",
        conflict.first_performance,
        "vs",
        conflict.second_performance
    )

    print("Difference:", conflict.difference)
    print("Severity:", conflict.severity)