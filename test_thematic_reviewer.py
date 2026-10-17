from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)
from app.research_agent.thematic_reviewer import (
    ThematicLiteratureReviewer,
)


def main():
    print("\nSTEP 1: Preparing synthetic research summaries...")

    paper1 = PaperSummary(
        title="Synthetic Study A: CNN Classification",
        authors=["Test Author A"],
        year=2024,
        source_url="https://example.org/synthetic-a",
        proposed_method="A convolutional neural network was proposed for image classification.",
        dataset="The study used 1000 labelled images.",
        key_findings="The CNN achieved 85 percent accuracy.",
        evidence_quotes={
            "proposed_method": "A convolutional neural network was proposed for image classification.",
            "dataset": "The study used 1000 labelled images.",
            "key_findings": "The CNN achieved 85 percent accuracy.",
        },
    )

    paper2 = PaperSummary(
        title="Synthetic Study B: CNN Classification",
        authors=["Test Author B"],
        year=2025,
        source_url="https://example.org/synthetic-b",
        proposed_method="A CNN-based approach was proposed for medical image classification.",
        dataset="The experiment used 2000 labelled images.",
        limitations="The evaluation was restricted to one institution.",
        evidence_quotes={
            "proposed_method": "A CNN-based approach was proposed for medical image classification.",
            "dataset": "The experiment used 2000 labelled images.",
            "limitations": "The evaluation was restricted to one institution.",
        },
    )

    print("Prepared 2 synthetic papers.")
    print("\nSTEP 2: Generating thematic literature review...")

    reviewer = ThematicLiteratureReviewer()

    review = reviewer.review(
        topic="Deep Learning for Medical Image Classification",
        summaries=[paper1, paper2],
        max_themes=4,
    )

    print("\n========== THEMATIC REVIEW ==========")
    print("Topic:", review.topic)
    print("Papers analyzed:", review.papers_analyzed)
    print("Themes generated:", len(review.themes))

    for index, theme in enumerate(review.themes, start=1):
        print(f"\nTHEME {index}: {theme.name}")
        print("Description:", theme.description)
        print("Coverage:", theme.coverage)

        for item in theme.supporting_evidence:
            print("  Paper:", item.paper_title)
            print("  Field:", item.field_name)
            print("  Finding:", item.finding)
            print("  Source quote:", item.source_quote)

    print("\nLIMITATIONS:")
    for limitation in review.limitations:
        print("-", limitation)

    print("\n========== VALIDATION ==========")

    assert review.papers_analyzed == 2
    assert 1 <= len(review.themes) <= 4

    for theme in review.themes:
        assert theme.supporting_evidence

        paper_count = len({
            item.paper_index
            for item in theme.supporting_evidence
        })

        expected_coverage = (
            "Cross-paper theme"
            if paper_count >= 2
            else "Single-paper observation"
        )

        assert theme.coverage == expected_coverage

        for item in theme.supporting_evidence:
            assert item.paper_index in (1, 2)
            assert item.source_quote
            assert item.finding != NOT_REPORTED

    print("\nTEST PASSED: Themes have valid source references.")


if __name__ == "__main__":
    main()
