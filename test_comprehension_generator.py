from app.research_agent.models import (
    ResearchEvidenceItem,
    ResearchSynthesis,
)

from app.research_agent.comprehension_generator import (
    ResearchComprehensionGenerator,
)


# ==========================================================
# FIXED GROUNDED RESEARCH MATERIAL
# ==========================================================

evidence = [
    ResearchEvidenceItem(
        claim=(
            "Recursion is challenging for novice "
            "programmers because it requires tracing "
            "non-linear and hierarchical sequences "
            "of execution."
        ),
        paper_title=(
            "Recursion in Secondary Computer Science "
            "Education"
        ),
        paper_url=(
            "https://doi.org/10.1145/3626252.3630916"
        ),
        relevance=1.0,
    ),

    ResearchEvidenceItem(
        claim=(
            "Concrete conceptual models can be more "
            "effective than abstract conceptual models "
            "when teaching recursion to novice "
            "programmers."
        ),
        paper_title=(
            "Conceptual models and cognitive learning "
            "styles in teaching recursion"
        ),
        paper_url=(
            "https://doi.org/10.1145/273133.274315"
        ),
        relevance=1.0,
    ),
]


synthesis = ResearchSynthesis(
    topic="recursion",
    question=(
        "Why is recursion difficult for novice "
        "programmers and what teaching approaches "
        "can help?"
    ),
    answer=(
        "Recursion can be difficult for novice "
        "programmers because understanding it requires "
        "tracing non-linear and hierarchical execution. "
        "Concrete conceptual models can help students "
        "understand recursion more effectively than "
        "purely abstract models."
    ),
    evidence=evidence,
    papers_used=[],
)


print(
    "\n========== RESEARCH SYNTHESIS =========="
)

print(
    synthesis.answer
)


# ==========================================================
# GENERATE COMPREHENSION QUESTION
# ==========================================================

generator = (
    ResearchComprehensionGenerator()
)

question = generator.generate(
    synthesis=synthesis,
    concept_name="recursion",
    difficulty="medium",
)


print(
    "\n========== COMPREHENSION QUESTION =========="
)

print(
    "Concept:",
    question.concept_name,
)

print(
    "Difficulty:",
    question.difficulty,
)

print(
    "Question:",
    question.question,
)

print(
    "\nExpected answer:",
    question.correct_answer,
)

print(
    "\nExplanation:",
    question.explanation,
)

print(
    "\nMisconception targets:"
)

for misconception in (
    question.misconception_targets
):
    print(
        "-",
        misconception,
    )


# ==========================================================
# VALIDATION
# ==========================================================

assert (
    question.concept_name
    == "recursion"
)

assert (
    question.difficulty
    == "medium"
)

assert (
    question.question.strip()
)

assert (
    question.correct_answer.strip()
)

assert (
    question.explanation.strip()
)

assert isinstance(
    question.misconception_targets,
    list,
)


print(
    "\n========== COMPREHENSION GENERATOR TEST PASSED =========="
)

print(
    "The Research Agent generated a grounded "
    "conceptual comprehension assessment."
)