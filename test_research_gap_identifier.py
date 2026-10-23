from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)
from app.research_agent.research_gap_identifier import (
    ResearchGapIdentifier,
)


def main():

    print("\nSTEP 1: Preparing synthetic research papers...")

    paper1 = PaperSummary(
        title="Synthetic Medical Imaging Study A",
        authors=["Test Author A"],
        year=2024,
        source_url="https://example.org/synthetic-a",
        limitations=(
            "The model was evaluated using data "
            "from only one institution."
        ),
        evidence_quotes={
            "limitations": (
                "The model was evaluated using data "
                "from only one institution."
            )
        },
    )

    paper2 = PaperSummary(
        title="Synthetic Medical Imaging Study B",
        authors=["Test Author B"],
        year=2025,
        source_url="https://example.org/synthetic-b",
        limitations=NOT_REPORTED,
    )

    paper3 = PaperSummary(
        title="Synthetic Medical Imaging Study C",
        authors=["Test Author C"],
        year=2025,
        source_url="https://example.org/synthetic-c",
        limitations="The model has poor generalization.",
        evidence_quotes={},
    )

    print("Prepared 3 synthetic papers.")

    print("\nSTEP 2: Identifying research opportunities...")

    identifier = ResearchGapIdentifier()

    report = identifier.identify(
        topic="Deep Learning for Medical Image Classification",
        summaries=[paper1, paper2, paper3],
    )

    print("\n========== RESEARCH GAP REPORT ==========\n")

    markdown = identifier.to_markdown(report)

    print(markdown)

    print("\n========== VALIDATION ==========")

    assert report.papers_analyzed == 3

    # Only Paper A has a supported limitation.
    assert len(report.candidates) == 1

    candidate = report.candidates[0]

    assert candidate.paper_index == 1

    assert (
        candidate.paper_title
        == "Synthetic Medical Imaging Study A"
    )

    assert "one institution" in candidate.reported_limitation

    assert candidate.supporting_quote

    assert (
        candidate.classification
        == "Potential research opportunity"
    )

    assert (
        candidate.verification_status
        == "Requires broader literature verification"
    )

    assert "Synthetic Medical Imaging Study B" not in markdown
    assert "Synthetic Medical Imaging Study C" not in markdown

    print("Papers analyzed:", report.papers_analyzed)
    print("Supported candidates:", len(report.candidates))
    print("Unsupported limitations correctly excluded.")

    print("\nTEST PASSED: Research Gap Identifier works correctly.")


if __name__ == "__main__":
    main()
