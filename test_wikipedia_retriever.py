from app.learning_agent.resources.wikipedia_retriever import (
    WikipediaResourceRetriever,
)
from app.learning_agent.resources.models import LearningResource


retriever = WikipediaResourceRetriever()

try:
    resources = retriever.search(
        concept_name="Recursion (computer science)",
        max_results=5,
        target_level="easy",
    )

except RuntimeError as exc:
    print("EXTERNAL API ERROR:", exc)
    raise SystemExit(2)


print("\n========== WIKIPEDIA RESULTS ==========")
print("Total resources:", len(resources))

for index, resource in enumerate(resources, start=1):
    print(f"\n{index}. {resource.title}")
    print("URL:", resource.url)
    print("Source:", resource.source)
    print("Difficulty:", resource.difficulty)

    assert isinstance(resource, LearningResource)
    assert resource.url.startswith(
        "https://en.wikipedia.org/wiki/"
    )
    assert resource.resource_type == "article"

assert resources, "Wikipedia returned no usable resources."

print("\nSTEP 16 TEST PASSED")
