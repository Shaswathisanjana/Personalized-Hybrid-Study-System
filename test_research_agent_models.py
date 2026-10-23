from app.research_agent.models import (
    ResearchRequest,
    ResearchPaper,
    ResearchEvidenceItem,
    ResearchSynthesis,
    ResearchComprehensionQuestion,
    ResearchStudentAnswer,
    ResearchComprehensionEvaluation,
)


# ==========================================================
# 1. CREATE A RESEARCH REQUEST
# ==========================================================

request = ResearchRequest(
    user_id="student_001",
    topic="Recursion",
    question="What is recursion and why is a base case necessary?",
)

print("\n========== RESEARCH REQUEST ==========")
print("User:", request.user_id)
print("Topic:", request.topic)
print("Question:", request.question)


# ==========================================================
# 2. REPRESENT A RETRIEVED RESEARCH PAPER
# ==========================================================

paper = ResearchPaper(
    title="Understanding Recursive Problem Solving",
    authors=["Example Author"],
    abstract=(
        "This example paper discusses recursive problem "
        "solving and termination conditions."
    ),
    url="https://example.com/paper",
    year=2025,
    source="test_source",
    paper_id="paper_001",
)

print("\n========== RESEARCH PAPER ==========")
print("Title:", paper.title)
print("Authors:", paper.authors)
print("Year:", paper.year)
print("Source:", paper.source)


# ==========================================================
# 3. CREATE GROUNDED RESEARCH EVIDENCE
# ==========================================================

research_evidence = ResearchEvidenceItem(
    claim=(
        "A recursive procedure requires a termination "
        "condition to prevent indefinite recursive calls."
    ),
    paper_title=paper.title,
    paper_url=paper.url,
    relevance=0.95,
)

print("\n========== RESEARCH EVIDENCE ==========")
print("Claim:", research_evidence.claim)
print("Relevance:", research_evidence.relevance)


# ==========================================================
# 4. CREATE A GROUNDED SYNTHESIS
# ==========================================================

synthesis = ResearchSynthesis(
    topic=request.topic,
    question=request.question,
    answer=(
        "Recursion solves a problem by reducing it to "
        "smaller instances of the same problem. A base "
        "case provides a termination condition."
    ),
    evidence=[research_evidence],
    papers_used=[paper],
)

print("\n========== RESEARCH SYNTHESIS ==========")
print("Topic:", synthesis.topic)
print("Answer:", synthesis.answer)
print("Evidence items:", len(synthesis.evidence))
print("Papers used:", len(synthesis.papers_used))


# ==========================================================
# 5. CREATE A COMPREHENSION QUESTION
# ==========================================================

question = ResearchComprehensionQuestion(
    concept_name="Recursion",
    question=(
        "Why does a recursive function require "
        "a base case?"
    ),
    correct_answer=(
        "A base case stops the recursive calls."
    ),
    explanation=(
        "Without a base case, recursive calls may "
        "continue indefinitely."
    ),
    difficulty="medium",
    misconception_targets=[
        "Does not understand recursion termination"
    ],
)

print("\n========== COMPREHENSION QUESTION ==========")
print("Concept:", question.concept_name)
print("Question:", question.question)
print("Difficulty:", question.difficulty)


# ==========================================================
# 6. REPRESENT THE STUDENT'S ANSWER
# ==========================================================

student_answer = ResearchStudentAnswer(
    user_id="student_001",
    question=question,
    answer="A base case stops recursive calls.",
)

print("\n========== STUDENT ANSWER ==========")
print("Answer:", student_answer.answer)


# ==========================================================
# 7. REPRESENT THE COMPREHENSION EVALUATION
# ==========================================================

evaluation = ResearchComprehensionEvaluation(
    is_correct=True,
    performance=1.0,
    confidence=0.90,
    feedback="The answer correctly explains recursion termination.",
)

print("\n========== COMPREHENSION EVALUATION ==========")
print("Correct:", evaluation.is_correct)
print("Performance:", evaluation.performance)
print("Confidence:", evaluation.confidence)


# ==========================================================
# BASIC VALIDATION
# ==========================================================

assert request.topic == "Recursion"

assert paper.title == "Understanding Recursive Problem Solving"

assert len(synthesis.evidence) == 1
assert len(synthesis.papers_used) == 1

assert question.concept_name == "Recursion"

assert student_answer.user_id == "student_001"

assert evaluation.is_correct is True
assert evaluation.performance == 1.0


print("\n========== RESEARCH AGENT MODEL TEST PASSED ==========")
print("Research request model: OK")
print("Research paper model: OK")
print("Grounded evidence model: OK")
print("Research synthesis model: OK")
print("Comprehension assessment model: OK")
print("Student answer model: OK")
print("Evaluation model: OK")