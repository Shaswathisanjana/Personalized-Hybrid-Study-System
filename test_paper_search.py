from app.research_agent.paper_search import (
    AcademicPaperSearch,
    PaperSearchError,
)


search_service = AcademicPaperSearch()

query = "recursion computer science education"


print(
    "\n========== RESEARCH AGENT PAPER SEARCH =========="
)

print("Query:", query)


try:

    result = search_service.search(
        query=query,
        limit=5,
    )

except PaperSearchError as exc:

    print("\nPAPER SEARCH FAILED")

    print(exc)

    raise


print("\n========== SEARCH METADATA ==========")

print("Provider used:", result.provider_used)

print(
    "Provider errors:",
    result.provider_errors,
)

print(
    "Number of papers:",
    len(result.papers),
)


assert result.provider_used == "openalex"

assert len(result.papers) > 0


print("\n========== PAPERS ==========")


for index, paper in enumerate(
    result.papers,
    start=1,
):

    print(
        f"\n---------- PAPER {index} ----------"
    )

    print("Title:", paper.title)

    print("Year:", paper.year)

    print("Source:", paper.source)

    print("Paper ID:", paper.paper_id)

    print("URL:", paper.url)

    if paper.abstract:

        print(
            "Abstract:",
            paper.abstract[:200],
            "...",
        )

    else:

        print(
            "Abstract: Not available"
        )


print(
    "\n========== RESEARCH PAPER SEARCH PASSED =========="
)

print(
    "The Research Agent successfully retrieved "
    "real scholarly works through its "
    "provider-independent search layer."
)