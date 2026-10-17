import json
from types import SimpleNamespace

from app.research_agent.paper_summarizer import PaperSummary
from app.research_agent.thematic_reviewer import ThematicLiteratureReviewer


class FakeModels:
    def generate_content(self, model, contents):
        response = {
            "themes": [
                {
                    "name": "CNN-Based Image Classification",
                    "description": (
                        "Both supplied studies propose CNN-based "
                        "approaches for image classification."
                    ),
                    "supports": [
                        {"paper_index": 1, "field_name": "proposed_method"},
                        {"paper_index": 2, "field_name": "proposed_method"},
                    ],
                },
                {
                    "name": "Evaluation Limitation",
                    "description": (
                        "The second study reports evaluation "
                        "restricted to one institution."
                    ),
                    "supports": [
                        {"paper_index": 2, "field_name": "limitations"},
                    ],
                },
                {
                    "name": "Invalid Reference Test",
                    "description": "This theme must be rejected.",
                    "supports": [
                        {"paper_index": 99, "field_name": "key_findings"},
                    ],
                },
            ]
        }

        return SimpleNamespace(text=json.dumps(response))


class FakeClient:
    def __init__(self):
        self.models = FakeModels()


def main():
    paper1 = PaperSummary(
        title="Synthetic Study A",
        authors=["Test Author A"],
        year=2024,
        source_url="https://example.org/synthetic-a",
        proposed_method="A CNN was proposed for image classification.",
        evidence_quotes={
            "proposed_method": "A CNN was proposed for image classification."
        },
    )

    paper2 = PaperSummary(
        title="Synthetic Study B",
        authors=["Test Author B"],
        year=2025,
        source_url="https://example.org/synthetic-b",
        proposed_method="A CNN approach was proposed for medical image classification.",
        limitations="Evaluation was restricted to one institution.",
        evidence_quotes={
            "proposed_method": "A CNN approach was proposed for medical image classification.",
            "limitations": "Evaluation was restricted to one institution.",
        },
    )

    reviewer = ThematicLiteratureReviewer(client=FakeClient())

    review = reviewer.review(
        topic="Medical Image Classification",
        summaries=[paper1, paper2],
    )

    print("\n========== THEMATIC REVIEW TEST ==========")

    for theme in review.themes:
        print("\nTheme:", theme.name)
        print("Coverage:", theme.coverage)
        print("Supporting references:", len(theme.supporting_evidence))

    assert len(review.themes) == 2

    assert review.themes[0].coverage == "Cross-paper theme"
    assert len(review.themes[0].supporting_evidence) == 2

    assert review.themes[1].coverage == "Single-paper observation"
    assert len(review.themes[1].supporting_evidence) == 1

    assert all(
        theme.name != "Invalid Reference Test"
        for theme in review.themes
    )

    print("\nTEST PASSED: Thematic review logic works correctly.")
    print("Invalid paper references were rejected.")
    print("No Gemini API request was required.")


if __name__ == "__main__":
    main()
