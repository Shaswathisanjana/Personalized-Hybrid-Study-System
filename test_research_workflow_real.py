from app.research_agent.research_workflow import (
    IntegratedResearchWorkflow,
)


def main():

    topic = "Deep Learning for Medical Image Classification"

    print("\n========== REAL RESEARCH WORKFLOW TEST ==========")

    print("Research topic:", topic)
    print("Requested papers: 2")
    print("Searching OpenAlex and summarizing with Gemini...")

    workflow = IntegratedResearchWorkflow()

    result = workflow.run(
        topic=topic,
        limit=2,
        include_thematic_review=False,
    )

    print("\n========== RESULTS ==========")

    print("Retrieved papers:", len(result.papers))
    print("Structured summaries:", len(result.summaries))

    for index, summary in enumerate(result.summaries, start=1):

        print(f"\nPAPER {index}: {summary.title}")
        print("Year:", summary.year)
        print("URL:", summary.source_url)

        print("Research problem:", summary.research_problem)
        print("Proposed method:", summary.proposed_method)
        print("Dataset:", summary.dataset)
        print("Evaluation metrics:", summary.evaluation_metrics)
        print("Key findings:", summary.key_findings)
        print("Limitations:", summary.limitations)

        print(
            "Verified source quotations:",
            len(summary.evidence_quotes),
        )

    if result.comparison is not None:

        print("\n========== METHODOLOGY COMPARISON ==========\n")

        print(
            workflow.comparator.to_markdown(
                result.comparison
            )
        )

    if result.gap_report is not None:

        print("\n========== RESEARCH OPPORTUNITIES ==========\n")

        print(
            workflow.gap_identifier.to_markdown(
                result.gap_report
            )
        )

    if result.proposal is not None:

        print("\n========== PRELIMINARY RESEARCH PROPOSAL ==========\n")

        print(
            workflow.objective_generator.to_markdown(
                result.proposal
            )
        )

    print("\n========== WARNINGS ==========")

    for warning in result.warnings:
        print("-", warning)

    print("\nREAL WORKFLOW EXECUTION COMPLETED.")


if __name__ == "__main__":
    main()
