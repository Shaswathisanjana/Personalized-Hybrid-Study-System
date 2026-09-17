from app.research_agent.paper_search import (
    AcademicPaperSearch,
)

from app.research_agent.semantic_ranker import (
    SemanticPaperRanker,
)


query = "recursion computer science education"


print(
    "\n========== REAL PAPER RETRIEVAL =========="
)

print(
    "Query:",
    query,
)


# ==========================================================
# RETRIEVE REAL PAPERS
# ==========================================================

search_service = AcademicPaperSearch()

search_result = search_service.search(
    query=query,
    limit=10,
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
# HYBRID RANKING WITH DIVERSIFIED CANDIDATES
# ==========================================================

ranker = SemanticPaperRanker()

ranked_papers = ranker.rank(
    query=query,
    papers=search_result.papers,
    candidate_limit=5,
)


print(
    "\n========== HYBRID SEMANTIC RANKING =========="
)


for position, result in enumerate(
    ranked_papers,
    start=1,
):

    print(
        f"\n---------- RANK {position} ----------"
    )

    print(
        "Title:",
        result.paper.title,
    )

    print(
        "Year:",
        result.paper.year,
    )

    print(
        "Lexical score:",
        result.lexical_score,
    )

    print(
        "Semantic score:",
        result.semantic_score,
    )

    print(
        "Combined score:",
        result.combined_score,
    )

    print(
        "Reason:",
        result.reason,
    )


# ==========================================================
# VALIDATION
# ==========================================================

assert len(ranked_papers) > 0

assert len(ranked_papers) <= 5


assert all(
    0.0 <= result.lexical_score <= 1.0
    for result in ranked_papers
)


assert all(
    0.0 <= result.semantic_score <= 1.0
    for result in ranked_papers
)


assert all(
    0.0 <= result.combined_score <= 1.0
    for result in ranked_papers
)


assert all(
    ranked_papers[index].combined_score
    >= ranked_papers[index + 1].combined_score
    for index in range(
        len(ranked_papers) - 1
    )
)


# ==========================================================
# CORE-CONCEPT DIVERSIFICATION CHECK
# ==========================================================

candidate_titles = [
    result.paper.title.lower()
    for result in ranked_papers
]


has_recursion_paper = any(
    "recursion" in title
    for title in candidate_titles
)


assert has_recursion_paper


print(
    "\n========== SEMANTIC RANKER V2 TEST PASSED =========="
)

print(
    "The Research Agent preserved core-topic papers "
    "and semantically reranked the diversified candidates."
)