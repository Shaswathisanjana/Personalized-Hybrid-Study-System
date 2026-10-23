from types import SimpleNamespace

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.research_agent.models import ResearchPaper
from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)
from app.research_agent.research_workflow import IntegratedResearchWorkflow


TOPIC = "Deep Learning for Medical Images"

GOOD_ABSTRACT = (
    "This study investigates deep learning techniques for medical image "
    "classification using a comparative experimental methodology. "
    "The authors describe model architectures, dataset preparation, "
    "training procedures, and evaluation strategies. Their analysis "
    "discusses reported findings, methodological limitations, practical "
    "challenges, and opportunities for further research in medical "
    "image analysis and clinical applications."
)


def paper(title, abstract, identifier):
    return ResearchPaper(
        title=title,
        authors=["Offline Test Author"],
        abstract=abstract,
        url=f"https://example.org/{identifier}",
        year=2025,
        source="offline_test",
        paper_id=identifier,
    )


class MockSearch:

    def __init__(self):
        self.calls = []

    def search(self, query, limit=5):
        self.calls.append(query)

        if query == TOPIC:
            papers = [
                paper("Unusable Paper", "Unusable Paper", "bad"),
            ]

        elif query == TOPIC + " review":
            papers = [
                paper("Valid Paper One", GOOD_ABSTRACT, "good1"),
                paper("Valid Paper Two", GOOD_ABSTRACT, "good2"),
            ]

        else:
            raise AssertionError(f"Unexpected search query: {query}")

        return SimpleNamespace(
            papers=papers,
            provider_errors=[],
        )


class MockSummarizer:

    def summarize_multiple(self, papers):
        # Returning no summaries intentionally stops the workflow
        # before any Gemini-dependent analysis.
        self.received = list(papers)
        return []


def main():

    student = StudentCognitiveModel(
        user_id="autonomous_end_to_end_test"
    )

    search = MockSearch()
    summarizer = MockSummarizer()

    workflow = IntegratedResearchWorkflow(
        search_service=search,
        summarizer=summarizer,
    )

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=CognitiveEngine(),
        workflow=workflow,
    )

    result = coordinator.conduct_research(
        topic=TOPIC,
        concept_name="Deep Learning",
        limit=3,
        include_thematic_review=False,
    )

    assert result.action.action_type == "introductory_research"

    assert search.calls == [
        TOPIC,
        TOPIC + " review",
    ]

    assert len(result.research.search_attempts) == 2
    assert result.research.search_attempts[0].usable_count == 0
    assert result.research.search_attempts[1].usable_count == 2

    assert len(result.research.papers) == 3
    assert len(result.research.accepted_papers) == 2
    assert len(result.research.excluded_papers) == 1

    assert len(summarizer.received) == 2

    print("PASS: Planner selected introductory research.")
    print("PASS: Autonomous refinement executed both planned queries.")
    print("PASS: Search history and abstract validation preserved.")

    state = student.get_concept("Deep Learning")

    assert state.mastery == 0.5
    assert state.attempts == 0

    print("PASS: Research generation did not update CACM.")

    calls_before = len(search.calls)

    coordinator.conduct_research(
        topic=TOPIC,
        concept_name="Deep Learning",
        papers=[],
        include_thematic_review=False,
    )

    assert len(search.calls) == calls_before

    print("PASS: Manually supplied papers bypass online retrieval.")

    print()
    print("ALL AUTONOMOUS RESEARCH END-TO-END TESTS PASSED.")


if __name__ == "__main__":
    main()
