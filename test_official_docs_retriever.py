from app.learning_agent.resources.official_docs_retriever import (
    OfficialDocumentationRetriever,
)

retriever = OfficialDocumentationRetriever()

queries = [
    "Python recursion",
    "Python lists",
    "Python exceptions",
    "Python functions",
]

print("\n========== OFFICIAL DOCUMENTATION TEST ==========")

for query in queries:
    resources = retriever.search(
        concept_name=query,
        max_results=10,
        target_level="easy",
    )

    print(f"\nQUERY: {query}")
    print(f"Returned: {len(resources)}")

    for resource in resources:
        print(f" - {resource.title}")
        print(f"   {resource.url}")

print("\nSTEP 35 DIAGNOSTIC COMPLETED")
