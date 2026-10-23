from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine


# ==================================================
# 1. CREATE STUDENT AND SHARED COGNITIVE ENGINE
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

cognitive_engine = CognitiveEngine()


# ==================================================
# 2. INITIAL COGNITIVE STATE
# ==================================================

recursion = student.get_concept("Recursion")

print("\n========== INITIAL STATE ==========")

print("Concept:", recursion.concept_name)
print("Mastery:", recursion.mastery)
print("Confidence:", recursion.confidence)
print("Attempts:", recursion.attempts)


# ==================================================
# 3. LEARNING AGENT EVIDENCE
# ==================================================
#
# Student performs well in a recursion quiz.
#

learning_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="quiz",
    performance=0.90,
    difficulty=0.60,
    reliability=0.70
)

learning_result = cognitive_engine.process_evidence(
    student=student,
    evidence=learning_evidence
)

print("\n========== LEARNING AGENT ==========")

print(
    "Mastery:",
    learning_result["concept"].mastery
)

print(
    "Confidence:",
    learning_result["concept"].confidence
)

print(
    "Conflicts detected:",
    len(learning_result["conflicts"])
)


# ==================================================
# 4. CODING AGENT EVIDENCE
# ==================================================
#
# Student later struggles with a difficult
# recursion coding problem.
#

coding_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="coding",
    evidence_type="coding_solution",
    performance=0.30,
    difficulty=0.90,
    reliability=0.85
)

coding_result = cognitive_engine.process_evidence(
    student=student,
    evidence=coding_evidence
)

print("\n========== CODING AGENT ==========")

print(
    "Mastery:",
    coding_result["concept"].mastery
)

print(
    "Confidence:",
    coding_result["concept"].confidence
)

print(
    "Conflicts detected:",
    len(coding_result["conflicts"])
)


# Print detected conflicts
for conflict in coding_result["conflicts"]:

    print("\n!!! COGNITIVE CONFLICT !!!")

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

    print(
        "Difference:",
        conflict.difference
    )

    print(
        "Severity:",
        conflict.severity
    )


# ==================================================
# 5. RESEARCH AGENT EVIDENCE
# ==================================================
#
# Research Agent checks conceptual understanding
# through a research-oriented question.
#

research_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="research",
    evidence_type="research_question",
    performance=0.60,
    difficulty=0.75,
    reliability=0.65
)

research_result = cognitive_engine.process_evidence(
    student=student,
    evidence=research_evidence
)

print("\n========== RESEARCH AGENT ==========")

print(
    "Mastery:",
    research_result["concept"].mastery
)

print(
    "Confidence:",
    research_result["concept"].confidence
)

print(
    "Conflicts detected:",
    len(research_result["conflicts"])
)


# ==================================================
# 6. FINAL SHARED COGNITIVE STATE
# ==================================================

recursion = student.get_concept("Recursion")

print("\n========== FINAL COGNITIVE STATE ==========")

print("Student:", student.user_id)
print("Concept:", recursion.concept_name)
print("Mastery:", recursion.mastery)
print("Confidence:", recursion.confidence)
print("Attempts:", recursion.attempts)


# ==================================================
# 7. SHOW COMPLETE EVIDENCE HISTORY
# ==================================================

history = (
    cognitive_engine
    .evidence_store
    .get_evidence_for_concept(
        user_id="student_001",
        concept_name="Recursion"
    )
)

print("\n========== EVIDENCE HISTORY ==========")

for evidence in history:

    print(
        evidence.source_agent,
        "->",
        evidence.evidence_type,
        "-> performance:",
        evidence.performance
    )