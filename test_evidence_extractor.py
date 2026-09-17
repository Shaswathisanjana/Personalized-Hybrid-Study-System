from app.research_agent.paper_search import (
    AcademicPaperSearch,
)

from app.research_agent.semantic_ranker import (
    SemanticPaperRanker,
)

from app.research_agent.evidence_extractor import (
    ResearchEvidenceExtractor,
)


query = "recursion computer science education"

question = (
    "Why is recursion difficult for novice programmers "
    "and what teaching approaches can help students "
    "understand it?"
)


print(
    "\n========== RESEARCH QUESTION =========="
)

print(question)


# ==========================================================
# STEP 1 — RETRIEVE REAL SCHOLARLY PAPERS
# ==========================================================

search_service = AcademicPaperSearch()

search_result = search_service.search(
    query=query,
    limit=10,
)


print(
    "\n========== RETRIEVAL =========="
)

print(
    "Provider:",
    search_result.provider_used,
)

print(
    "Retrieved papers:",
    len(search_result.papers),
)


assert len(search_result.papers) > 0


# ==========================================================
# STEP 2 — HYBRID PAPER RANKING
# ==========================================================

ranker = SemanticPaperRanker()

ranked_papers = ranker.rank(
    query=query,
    papers=search_result.papers,
    candidate_limit=5,
)


print(
    "\n========== SELECTED PAPERS =========="
)


for index, ranked in enumerate(
    ranked_papers[:3],
    start=1,
):
    print(
        f"{index}. {ranked.paper.title}"
    )

    print(
        "   Semantic relevance:",
        ranked.semantic_score,
    )


assert len(ranked_papers) > 0


# ==========================================================
# STEP 3 — GROUNDED EVIDENCE EXTRACTION
# ==========================================================

extractor = ResearchEvidenceExtractor()

evidence = (
    extractor.extract_from_ranked_papers(
        question=question,
        ranked_papers=ranked_papers[:3],
        max_claims_per_paper=2,
    )
)


print(
    "\n========== GROUNDED EVIDENCE =========="
)


for index, item in enumerate(
    evidence,
    start=1,
):

    print(
        f"\n---------- EVIDENCE {index} ----------"
    )

    print(
        "Claim:",
        item.claim,
    )

    print(
        "Paper:",
        item.paper_title,
    )

    print(
        "URL:",
        item.paper_url,
    )

    print(
        "Relevance:",
        item.relevance,
    )


# ==========================================================
# VALIDATION
# ==========================================================

assert len(evidence) > 0


assert all(
    item.claim.strip()
    for item in evidence
)


assert all(
    item.paper_title.strip()
    for item in evidence
)


assert all(
    0.0 <= item.relevance <= 1.0
    for item in evidence
)


print(
    "\n========== EVIDENCE EXTRACTION TEST PASSED =========="
)

print(
    "The Research Agent extracted traceable claims "
    "from retrieved scholarly paper abstracts."
)