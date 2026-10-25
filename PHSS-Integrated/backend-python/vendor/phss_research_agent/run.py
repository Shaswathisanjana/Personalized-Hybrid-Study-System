from src.research_agent import ResearchAgent


def main():

    agent = ResearchAgent()

    topic = input(
        "\nEnter research topic: "
    ).strip()

    if not topic:

        print(
            "Research topic cannot be empty."
        )

        return

    papers_input = input(
        "Number of papers [5]: "
    ).strip()

    if papers_input:

        try:
            max_papers = int(
                papers_input
            )

        except ValueError:

            print(
                "Invalid number. "
                "Using 5 papers."
            )

            max_papers = 5

    else:

        max_papers = 5

    agent.run(
        topic=topic,
        max_papers=max_papers,
    )


if __name__ == "__main__":
    main()