from collections import Counter

from app.learning_agent.resources.resource_recommender import (
    LearningResourceRecommender,
)

print("\n========== THREE-SOURCE INTEGRATION TEST ==========")

recommender = LearningResourceRecommender()

print("\nRegistered retrievers:")

retrievers = recommender.retriever.retrievers

for retriever in retrievers:
    print(" -", type(retriever).__name__)

expected = {
    "YouTubeResourceRetriever",
    "WikipediaResourceRetriever",
    "OfficialDocumentationRetriever",
}

actual = {type(retriever).__name__ for retriever in retrievers}

assert actual == expected, (
    f"Expected {expected}, but registered {actual}"
)

print("\n========== RETRIEVAL: PYTHON RECURSION ==========")

resources = recommender.retriever.search(
    concept_name="Python recursion",
    max_results=15,
    target_level="easy",
)

print("Total retrieved:", len(resources))

counts = Counter(resource.source.split(" - ")[0] for resource in resources)

print("Source counts:", dict(counts))

for index, resource in enumerate(resources, start=1):
    print(
        f"{index}. [{resource.source}] "
        f"{resource.title}"
    )
    print(f"   {resource.url}")

assert any(
    resource.source == "Official Python Documentation"
    for resource in resources
), "Official documentation did not reach the combined retrieval pool."

assert len({resource.url for resource in resources}) == len(resources), (
    "Duplicate URLs found in the combined retrieval pool."
)

print("\nSTEP 41 THREE-SOURCE RETRIEVAL VERIFIED")
