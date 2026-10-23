from app.cognitive.misconception_tracker import (
    MisconceptionTracker,
)


tracker = MisconceptionTracker()


# ==========================================
# CREATE HYPOTHESIS
# ==========================================

hypothesis = tracker.create_hypothesis(
    description=(
        "Confuses n-2 recursive step with n-1"
    ),
    source_agent="learning",
)


print(
    "\n========== INITIAL HYPOTHESIS =========="
)

print(
    "Description:",
    hypothesis.description,
)

print(
    "Supporting evidence:",
    hypothesis.supporting_evidence,
)

print(
    "Contradicting evidence:",
    hypothesis.contradicting_evidence,
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)

print(
    "Sources:",
    hypothesis.source_agents,
)


# ==========================================
# SECOND WRONG ANSWER
# ==========================================

tracker.add_support(
    hypothesis,
    source_agent="learning",
)


print(
    "\n========== AFTER SUPPORTING EVIDENCE =========="
)

print(
    "Supporting evidence:",
    hypothesis.supporting_evidence,
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)


# ==========================================
# FIRST CORRECT REASSESSMENT
# ==========================================

tracker.add_contradiction(
    hypothesis,
    source_agent="learning",
)


print(
    "\n========== AFTER CORRECT REASSESSMENT 1 =========="
)

print(
    "Contradicting evidence:",
    hypothesis.contradicting_evidence,
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)


# ==========================================
# SECOND CORRECT REASSESSMENT
# ==========================================

tracker.add_contradiction(
    hypothesis,
    source_agent="learning",
)


print(
    "\n========== AFTER CORRECT REASSESSMENT 2 =========="
)

print(
    "Contradicting evidence:",
    hypothesis.contradicting_evidence,
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)


# ==========================================
# THIRD CORRECT REASSESSMENT
# ==========================================

tracker.add_contradiction(
    hypothesis,
    source_agent="learning",
)


print(
    "\n========== AFTER CORRECT REASSESSMENT 3 =========="
)

print(
    "Contradicting evidence:",
    hypothesis.contradicting_evidence,
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)