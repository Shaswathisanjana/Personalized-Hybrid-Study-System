from app.research_agent.providers.openalex import (
    OpenAlexSearch,
    OpenAlexSearchError,
)


search_service = OpenAlexSearch()

query = "recursion computer science education"


print("\n========== OPENALEX PROVIDER TEST ==========")

print("Query:", query)


try:

    papers = search_service.search(
        query=query,
        limit=5,
    )

except OpenAlexSearchError as exc:

    print("\nOPENALEX SEARCH FAILED")

    print(exc)

    raise


print("\n========== RESULTS ==========")

print("Number of papers:", len(papers))


assert len(papers) > 0


for index, paper in enumerate(
    papers,
    start=1,
):

    print(
        f"\n---------- PAPER {index} ----------"
    )

    print("Title:", paper.title)

    print(
        "Authors:",
        ", ".join(paper.authors)
        if paper.authors
        else "Not available",
    )

    print("Year:", paper.year)

    print("Source:", paper.source)

    print("Paper ID:", paper.paper_id)

    print("URL:", paper.url)

    if paper.abstract:

        print(
            "Abstract:",
            paper.abstract[:250],
            "...",
        )

    else:

        print("Abstract: Not available")

    assert paper.title

    assert paper.source == "openalex"


print(
    "\n========== OPENALEX PROVIDER TEST PASSED =========="
)