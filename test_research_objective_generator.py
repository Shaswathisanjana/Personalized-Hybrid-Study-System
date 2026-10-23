from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)
from app.research_agent.research_gap_identifier import (
    ResearchGapIdentifier,
)
from app.research_agent.research_objective_generator import (
    ResearchObjectiveGenerator,
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

    print("\nSTEP 2: Identifying supported research opportunities...")

    gap_report = ResearchGapIdentifier.identify(
        topic="Deep Learning for Medical Image Classification",
        summaries=[paper1, paper2],
    )

    assert len(gap_report.candidates) == 1

    print("Supported opportunities:", len(gap_report.candidates))

    print("\nSTEP 3: Generating research objectives...")

    proposal = ResearchObjectiveGenerator.generate(
        gap_report
    )

    markdown = ResearchObjectiveGenerator.to_markdown(
        proposal
    )

    print("\n========== RESEARCH PROPOSAL ==========\n")
    print(markdown)

    print("\n========== VALIDATION ==========")

    assert len(proposal.directions) == 1

    direction = proposal.directions[0]

    assert direction.number == 1
    assert "one institution" in direction.objective
    assert "one institution" in direction.research_question

    assert (
        direction.source_paper
        == "Synthetic Medical Imaging Study A"
    )

    assert direction.supporting_quote
    assert direction.source_url == "https://example.org/synthetic-a"

    assert (
        direction.status
        == "Proposed direction - not a validated research gap"
    )

    print("Objectives generated:", len(proposal.directions))
    print("Source evidence preserved.")
    print("Proposal correctly labelled as unverified.")

    print("\nSTEP 4: Testing empty research opportunities...")

    empty_report = ResearchGapIdentifier.identify(
        topic="Synthetic Topic Without Reported Limitations",
        summaries=[paper2],
    )

    empty_proposal = ResearchObjectiveGenerator.generate(
        empty_report
    )

    assert len(empty_proposal.directions) == 0

    print("No unsupported objectives were generated.")

    print("\nTEST PASSED: Research Objective Generator works correctly.")


if __name__ == "__main__":
    main()
