from app.research_agent.models import ResearchPaper
from app.research_agent.paper_summarizer import (
    StructuredPaperSummarizer,
    SUMMARY_FIELDS,
    NOT_REPORTED,
)


def main():

    paper = ResearchPaper(
        title="Synthetic Recursion Learning Study",
        authors=["Test Author"],
        year=2025,
        url="https://example.org/synthetic-test-only",
        source="synthetic_test",
        paper_id="TEST-002",
        abstract=(
            "This study investigates difficulties students "
            "experience when learning recursion. "
            "We propose a guided explanation approach "
            "to support conceptual understanding."
        ),
    )

    summarizer = StructuredPaperSummarizer()

    summary = summarizer.summarize(paper)

    print("\n========== MISSING INFORMATION TEST ==========")

    for field_name in SUMMARY_FIELDS:
        print(
            field_name,
            ":",
            getattr(summary, field_name),
        )

    # The abstract does not report these details.
    required_missing = (
        "dataset",
        "evaluation_metrics",
        "key_findings",
        "limitations",
    )

    for field_name in required_missing:
        assert getattr(
            summary,
            field_name,
        ) == NOT_REPORTED, (
            f"Unsupported information generated for {field_name}"
        )

    print("\nTEST PASSED: Missing information was not invented.")


if __name__ == "__main__":
    main()
