from app.research_agent.models import ResearchPaper
from app.research_agent.paper_summarizer import (
    StructuredPaperSummarizer,
    SUMMARY_FIELDS,
    NOT_REPORTED,
)


def main():
    print("\nSTEP 1: Creating synthetic test paper...")

    paper = ResearchPaper(
        title="Synthetic Medical Image Classification Study",
        authors=["Test Author"],
        year=2025,
        url="https://example.org/synthetic-test-only",
        source="synthetic_test",
        paper_id="TEST-001",
        abstract=(
            "This study investigates the problem of classifying "
            "medical images into two categories. "
            "We propose a convolutional neural network for "
            "image classification. "
            "The model was evaluated using a dataset of "
            "1000 labelled images. "
            "Accuracy and F1-score were used as evaluation metrics. "
            "The proposed model achieved an accuracy of 85 percent. "
            "A limitation of this study is that the model was "
            "evaluated using data from only one institution."
        ),
    )

    print("Paper:", paper.title)
    print("NOTE: This is synthetic test data, not a real publication.")

    print("\nSTEP 2: Testing Gemini summarization...")

    summarizer = StructuredPaperSummarizer()
    summary = summarizer.summarize(paper)

    print("\n========== STRUCTURED SUMMARY ==========")

    for field_name in SUMMARY_FIELDS:
        value = getattr(summary, field_name)

        print("\n" + field_name.replace("_", " ").upper())
        print(value)

        quote = summary.evidence_quotes.get(field_name)

        if quote:
            print("Supporting quote:", quote)

    print("\n========== VALIDATION ==========")

    supported = len(summary.evidence_quotes)

    missing = sum(
        getattr(summary, field_name) == NOT_REPORTED
        for field_name in SUMMARY_FIELDS
    )

    print("Supported fields:", supported)
    print("Not reported:", missing)
    print("Expected fields:", len(SUMMARY_FIELDS))

    assert supported + missing == len(SUMMARY_FIELDS)

    for quote in summary.evidence_quotes.values():
        normalize = lambda text: " ".join(
            text.split()
        ).casefold()

        assert normalize(quote) in normalize(paper.abstract)

    print("\nTEST PASSED")


if __name__ == "__main__":
    main()
