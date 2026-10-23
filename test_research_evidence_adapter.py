from app.research_integration.evidence_adapter import (
    ResearchComprehensionResult,
    ResearchEvidenceAdapter,
)


# ------------------------------------------------------------
# Create a sample research comprehension result
# ------------------------------------------------------------

result = ResearchComprehensionResult(
    user_id="student_001",
    concept_name="Recursion",
    performance=0.20,
    difficulty=0.70,
    confidence=0.90,
)


# ------------------------------------------------------------
# Convert research result into common cognitive evidence
# ------------------------------------------------------------

adapter = ResearchEvidenceAdapter()

evidence = adapter.to_learning_evidence(result)


# ------------------------------------------------------------
# Display the generated evidence
# ------------------------------------------------------------

print("\n========== RESEARCH EVIDENCE ==========")

print("User:", evidence.user_id)
print("Concept:", evidence.concept_name)
print("Source Agent:", evidence.source_agent)
print("Evidence Type:", evidence.evidence_type)
print("Performance:", evidence.performance)
print("Difficulty:", evidence.difficulty)
print("Reliability:", evidence.reliability)
print("Misconceptions:", evidence.detected_misconceptions)


# ------------------------------------------------------------
# Verify important properties
# ------------------------------------------------------------

assert evidence.user_id == "student_001"
assert evidence.concept_name == "Recursion"

# Most important check:
assert evidence.source_agent == "research"

assert evidence.performance == 0.20
assert evidence.difficulty == 0.70

# reliability = 0.50 + (0.30 * 0.90)
#             = 0.77
assert evidence.reliability == 0.77


print("\nRESEARCH EVIDENCE ADAPTER TEST PASSED")