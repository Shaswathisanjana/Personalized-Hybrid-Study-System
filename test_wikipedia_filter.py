from app.learning_agent.resources.wikipedia_retriever import (
    WikipediaResourceRetriever,
)

retriever = WikipediaResourceRetriever()

print("\n========== WIKIPEDIA FILTER TEST ==========")

try:
    resources = retriever.search(
        concept_name="Recursion",
        max_results=15,
        target_level="easy",
    )

except RuntimeError as exc:
    print("EXTERNAL API ERROR:", exc)
    raise SystemExit(2)

print("Returned articles:", len(resources))

for index, resource in enumerate(resources, start=1):
    print(f"{index}. {resource.title}")
    print("   ", resource.url)

    assert "disambiguation" not in resource.title.lower(), (
        f"Disambiguation page was not filtered: {resource.title}"
    )

assert resources, "No usable Wikipedia articles were returned."

print("\nSTEP 20 TEST PASSED")
