from app.research_agent.paper_search import AcademicPaperSearch
from app.research_agent.paper_summarizer import (
    StructuredPaperSummarizer,
    SUMMARY_FIELDS,
    NOT_REPORTED,
)


def main():
    print("\nSTEP 1: Searching for a real academic paper...")

    search = AcademicPaperSearch()

    result = search.search(
        query="deep learning for medical image classification",
        limit=5,
    )

    papers = [
        paper
        for paper in result.papers
        if paper.abstract.strip()
    ]

    if not papers:
        print("No papers with usable abstracts were returned.")
        return

    paper = papers[0]

    print("\nSELECTED PAPER:")
    print("Title:", paper.title)
    print("Year:", paper.year)
    print("URL:", paper.url)
    print("Abstract length:", len(paper.abstract))

    print("\nSTEP 2: Generating structured summary...")

    summarizer = StructuredPaperSummarizer()
    summary = summarizer.summarize(paper)

    print("\n========== STRUCTURED SUMMARY ==========")
    print("Title:", summary.title)
    print("Authors:", ", ".join(summary.authors))
    print("Year:", summary.year)
    print("Source:", summary.source_url)
    print("Source scope:", summary.source_scope)

    for field_name in SUMMARY_FIELDS:
        print("\n" + field_name.replace("_", " ").upper())
        print(getattr(summary, field_name))

        quote = summary.evidence_quotes.get(field_name)

        if quote:
            print("Supporting abstract quote:", quote)

    print("\n========== VALIDATION ==========")

    supported = len(summary.evidence_quotes)
    missing = sum(
        getattr(summary, name) == NOT_REPORTED
        for name in SUMMARY_FIELDS
    )

    print("Fields with matching source quotes:", supported)
    print("Fields marked as not reported:", missing)
    print("Total expected fields:", len(SUMMARY_FIELDS))

    assert supported + missing == len(SUMMARY_FIELDS)

    print("\nTEST PASSED")


if __name__ == "__main__":
    main()
