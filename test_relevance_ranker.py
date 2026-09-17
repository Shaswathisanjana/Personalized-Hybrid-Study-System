from app.research_agent.paper_search import (
    AcademicPaperSearch,
)

from app.research_agent.relevance_ranker import (
    PaperRelevanceRanker,
)


# ==========================================================
# REAL PAPER RETRIEVAL
# ==========================================================

search_service = AcademicPaperSearch()

query = "recursion computer science education"


print(
    "\n========== PAPER RETRIEVAL =========="
)

print("Query:", query)


search_result = search_service.search(
    query=query,
    limit=10,
)


print(
    "Provider:",
    search_result.provider_used,
)

print(
    "Candidate papers:",
    len(search_result.papers),
)


assert len(search_result.papers) > 0


# ==========================================================
# RELEVANCE RANKING
# ==========================================================

ranker = PaperRelevanceRanker()

ranked_papers = ranker.rank(
    query=query,
    papers=search_result.papers,
)


print(
    "\n========== RELEVANCE RANKING =========="
)


for position, ranked in enumerate(
    ranked_papers,
    start=1,
):

    print(
        f"\n---------- RANK {position} ----------"
    )

    print(
        "Title:",
        ranked.paper.title,
    )

    print(
        "Year:",
        ranked.paper.year,
    )

    print(
        "Score:",
        ranked.relevance_score,
    )

    print(
        "Matched terms:",
        ranked.matched_terms,
    )


# ==========================================================
# TOP PAPER SELECTION
# ==========================================================

top_papers = ranker.top_k(
    query=query,
    papers=search_result.papers,
    k=3,
    minimum_score=0.10,
)


print(
    "\n========== TOP PAPERS =========="
)


for position, ranked in enumerate(
    top_papers,
    start=1,
):

    print(
        f"{position}. "
        f"{ranked.paper.title}"
    )

    print(
        "   Score:",
        ranked.relevance_score,
    )

    print(
        "   Matched:",
        ranked.matched_terms,
    )


# ==========================================================
# VALIDATION
# ==========================================================

assert len(ranked_papers) == len(
    search_result.papers
)

assert all(
    ranked_papers[index].relevance_score
    >= ranked_papers[index + 1].relevance_score
    for index in range(
        len(ranked_papers) - 1
    )
)

assert all(
    0.0 <= ranked.relevance_score <= 1.0
    for ranked in ranked_papers
)

assert len(top_papers) <= 3


print(
    "\n========== RELEVANCE RANKER TEST PASSED =========="
)

print(
    "Candidate papers were ranked using "
    "explainable title and abstract relevance."
)