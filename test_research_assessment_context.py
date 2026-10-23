from app.research_agent.assessment_context import (
    ResearchAssessmentContextBuilder,
)
from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)
from app.research_agent.research_workflow import (
    ResearchWorkflowResult,
)


def main():

    builder = ResearchAssessmentContextBuilder()

    supported_summary = PaperSummary(
        title="Synthetic CNN Study",
        authors=["Test Author"],
        year=2025,
        source_url="https://example.org/synthetic-cnn",
        proposed_method="A convolutional neural network was used.",
        dataset="A medical image dataset was used.",
        key_findings=NOT_REPORTED,
        evidence_quotes={
            "proposed_method": (
                "A convolutional neural network was used."
            ),
        },
    )

    result = ResearchWorkflowResult(
        topic="Medical Image Classification",
        summaries=[supported_summary],
    )

    synthesis = builder.build(result)

    assert len(synthesis.evidence) == 1
    assert "convolutional neural network" in synthesis.answer
    assert "medical image dataset" not in synthesis.answer
    assert synthesis.topic == result.topic

    print("PASS: Supported evidence included.")
    print("PASS: Unsupported dataset excluded.")

    unsupported_summary = PaperSummary(
        title="Synthetic Unsupported Study",
        authors=["Test Author"],
        year=2025,
        source_url="https://example.org/unsupported",
        proposed_method="An unsupported method claim.",
        evidence_quotes={},
    )

    unsupported_result = ResearchWorkflowResult(
        topic="Unsupported Research",
        summaries=[unsupported_summary],
    )

    try:
        builder.build(unsupported_result)
    except ValueError as exc:
        assert "No source-supported findings" in str(exc)
        print("PASS: Unsupported-only research rejected.")
    else:
        raise AssertionError(
            "Unsupported research must not generate an assessment."
        )

    try:
        builder.build(
            ResearchWorkflowResult(topic="Empty Research")
        )
    except ValueError as exc:
        assert "without research summaries" in str(exc)
        print("PASS: Empty research rejected.")
    else:
        raise AssertionError(
            "Empty research must not generate an assessment."
        )

    print(
        "\nALL ASSESSMENT CONTEXT TESTS PASSED."
    )


if __name__ == "__main__":
    main()
