from app.cognitive.evidence import LearningEvidence
from app.cognitive.conflict_detector import CognitiveConflict
from app.cognitive.conflict_resolver import ConflictResolver


# ==================================================
# SETUP
# ==================================================

resolver = ConflictResolver()


# Original conflict:
#
# Learning Agent says performance = 0.90
# Coding Agent says performance = 0.30
#
# Difference = 0.60 -> HIGH conflict

conflict = CognitiveConflict(
    concept_name="Recursion",
    first_agent="learning",
    second_agent="coding",
    first_performance=0.90,
    second_performance=0.30,
    difference=0.60,
    severity="high"
)


# ==================================================
# TEST 1
# DIAGNOSTIC SUPPORTS CODING AGENT
# ==================================================

diagnostic_coding = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="diagnostic_quiz",
    performance=0.35,
    difficulty=0.70,
    reliability=0.80
)

result1 = resolver.resolve(
    conflict,
    diagnostic_coding
)

print("\n========== TEST 1: SUPPORTS CODING ==========")

print("Resolved:", result1.resolved)
print("Supported Agent:", result1.supported_agent)
print(
    "Diagnostic Performance:",
    result1.diagnostic_performance
)
print(
    "Distance from Learning:",
    result1.first_distance
)
print(
    "Distance from Coding:",
    result1.second_distance
)
print("Reason:", result1.reason)


# ==================================================
# TEST 2
# DIAGNOSTIC SUPPORTS LEARNING AGENT
# ==================================================

diagnostic_learning = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="diagnostic_quiz",
    performance=0.85,
    difficulty=0.70,
    reliability=0.80
)

result2 = resolver.resolve(
    conflict,
    diagnostic_learning
)

print("\n========== TEST 2: SUPPORTS LEARNING ==========")

print("Resolved:", result2.resolved)
print("Supported Agent:", result2.supported_agent)
print(
    "Diagnostic Performance:",
    result2.diagnostic_performance
)
print(
    "Distance from Learning:",
    result2.first_distance
)
print(
    "Distance from Coding:",
    result2.second_distance
)
print("Reason:", result2.reason)


# ==================================================
# TEST 3
# DIAGNOSTIC IS UNCERTAIN
# ==================================================

diagnostic_uncertain = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="diagnostic_quiz",
    performance=0.60,
    difficulty=0.70,
    reliability=0.80
)

result3 = resolver.resolve(
    conflict,
    diagnostic_uncertain
)

print("\n========== TEST 3: UNCERTAIN ==========")

print("Resolved:", result3.resolved)
print("Supported Agent:", result3.supported_agent)
print(
    "Diagnostic Performance:",
    result3.diagnostic_performance
)
print(
    "Distance from Learning:",
    result3.first_distance
)
print(
    "Distance from Coding:",
    result3.second_distance
)
print("Reason:", result3.reason)