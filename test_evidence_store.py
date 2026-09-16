from app.cognitive.evidence import LearningEvidence
from app.cognitive.evidence_store import EvidenceStore


# --------------------------------------------------
# 1. CREATE THE SHARED EVIDENCE STORE
# --------------------------------------------------

store = EvidenceStore()


# --------------------------------------------------
# 2. LEARNING AGENT EVIDENCE
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
# 3. CODING AGENT EVIDENCE
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
# 4. RESEARCH AGENT EVIDENCE
# --------------------------------------------------

research_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="research",
    evidence_type="research_question",
    performance=0.60,
    difficulty=0.75,
    reliability=0.65
)


# --------------------------------------------------
# 5. STORE EVIDENCE FROM ALL THREE AGENTS
# --------------------------------------------------

store.add_evidence(learning_evidence)
store.add_evidence(coding_evidence)
store.add_evidence(research_evidence)


# --------------------------------------------------
# 6. GET ALL RECURSION EVIDENCE
# --------------------------------------------------

recursion_evidence = store.get_evidence_for_concept(
    user_id="student_001",
    concept_name="Recursion"
)


print("\n----- RECURSION EVIDENCE HISTORY -----")

for evidence in recursion_evidence:

    print("\nAgent:", evidence.source_agent)
    print("Type:", evidence.evidence_type)
    print("Performance:", evidence.performance)
    print("Difficulty:", evidence.difficulty)
    print("Reliability:", evidence.reliability)


# --------------------------------------------------
# 7. GET LATEST CODING AGENT EVIDENCE
# --------------------------------------------------

latest_coding = store.get_latest_evidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="coding"
)


print("\n----- LATEST CODING EVIDENCE -----")

if latest_coding is not None:
    print("Agent:", latest_coding.source_agent)
    print("Concept:", latest_coding.concept_name)
    print("Performance:", latest_coding.performance)
else:
    print("No coding evidence found.")