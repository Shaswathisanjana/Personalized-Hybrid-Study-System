from app.research_agent.models import (
    ResearchEvidenceItem,
    ResearchPaper,
)

from app.research_agent.research_synthesizer import (
    ResearchSynthesizer,
)


topic = "recursion"

question = (
    "Why is recursion difficult for novice programmers "
    "and what teaching approaches can help students "
    "understand it?"
)


# ==========================================================
# FIXED GROUNDED PAPERS
# ==========================================================

paper_1 = ResearchPaper(
    title=(
        "Recursion in Secondary Computer Science "
        "Education: A Comparative Study of Visual "
        "Programming Approaches"
    ),
    authors=[
        "Sverrir Thorgeirsson",
        "Lennart C. Lais",
        "Theo B. Weidmann",
        "Zhendong Su",
    ],
    abstract=(
        "Test fixture based on previously extracted "
        "research evidence."
    ),
    url="https://doi.org/10.1145/3626252.3630916",
    year=2024,
    source="openalex",
    paper_id="W4392564484",
)


paper_2 = ResearchPaper(
    title=(
        "Conceptual models and cognitive learning "
        "styles in teaching recursion"
    ),
    authors=[],
    abstract=(
        "Test fixture based on previously extracted "
        "research evidence."
    ),
    url="https://doi.org/10.1145/273133.274315",
    year=1998,
    source="openalex",
    paper_id="recursion-conceptual-models",
)


# ==========================================================
# FIXED EXTRACTED EVIDENCE
# ==========================================================

evidence = [
    ResearchEvidenceItem(
        claim=(
            "Recursion is challenging for novice "
            "programmers because it requires tracing "
            "non-linear and hierarchical sequences "
            "of execution."
        ),
        paper_title=paper_1.title,
        paper_url=paper_1.url,
        relevance=1.0,
    ),

    ResearchEvidenceItem(
        claim=(
            "The programming-by-demonstration paradigm, "
            "as implemented in the Algot language, can "
            "aid comprehension of recursion compared "
            "with traditional visual programming "
            "languages such as Scratch."
        ),
        paper_title=paper_1.title,
        paper_url=paper_1.url,
        relevance=0.9,
    ),

    ResearchEvidenceItem(
        claim=(
            "Concrete conceptual models are more "
            "effective than abstract conceptual models "
            "when teaching recursion to novice "
            "programmers."
        ),
        paper_title=paper_2.title,
        paper_url=paper_2.url,
        relevance=1.0,
    ),

    ResearchEvidenceItem(
        claim=(
            "A student's cognitive learning style "
            "influences performance when learning "
            "recursion."
        ),
        paper_title=paper_2.title,
        paper_url=paper_2.url,
        relevance=0.8,
    ),
]


print(
    "\n========== RESEARCH QUESTION =========="
)

print(
    question
)


print(
    "\n========== AVAILABLE EVIDENCE =========="
)


for index, item in enumerate(
    evidence,
    start=1,
):
    print(
        f"{index}. {item.claim}"
    )

    print(
        "   Source:",
        item.paper_title,
    )


# ==========================================================
# SYNTHESIS
# ==========================================================

synthesizer = (
    ResearchSynthesizer()
)

synthesis = synthesizer.synthesize(
    topic=topic,
    question=question,
    evidence=evidence,
    papers=[
        paper_1,
        paper_2,
    ],
)


print(
    "\n========== GROUNDED SYNTHESIS =========="
)

print(
    synthesis.answer
)


print(
    "\n========== EVIDENCE USED =========="
)


for item in synthesis.evidence:

    print(
        "-",
        item.claim,
    )


print(
    "\n========== PAPERS USED =========="
)


for paper in synthesis.papers_used:

    print(
        "-",
        paper.title,
    )

    print(
        " ",
        paper.url,
    )


# ==========================================================
# VALIDATION
# ==========================================================

assert synthesis.topic == topic

assert synthesis.question == question

assert synthesis.answer.strip()

assert len(
    synthesis.evidence
) > 0

assert len(
    synthesis.papers_used
) > 0


available_titles = {
    paper_1.title,
    paper_2.title,
}


assert all(
    paper.title
    in available_titles
    for paper
    in synthesis.papers_used
)


available_claims = {
    item.claim
    for item in evidence
}


assert all(
    item.claim
    in available_claims
    for item
    in synthesis.evidence
)


print(
    "\n========== RESEARCH SYNTHESIS TEST PASSED =========="
)

print(
    "The Research Agent produced a student-facing "
    "answer while retaining its grounded evidence "
    "and scholarly-paper provenance."
)