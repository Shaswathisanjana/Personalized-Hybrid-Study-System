from app.learning_agent.resources.official_docs_retriever import (
    OfficialDocumentationRetriever,
)


retriever = OfficialDocumentationRetriever()

CASES = [
    (
        "Python recursion",
        "Python Standard Library - functools",
    ),
    (
        "Python lists",
        "Python Tutorial - Data Structures",
    ),
    (
        "Python exceptions",
        "Python Tutorial - Errors and Exceptions",
    ),
    (
        "Python functions",
        "Python Tutorial - Defining Functions",
    ),
]

print("\n========== DOCUMENTATION REGRESSION TEST ==========")

for query, expected_title in CASES:
    resources = retriever.search(
        concept_name=query,
        max_results=10,
        target_level="easy",
    )

    titles = [resource.title for resource in resources]

    assert titles == [expected_title], (
        f"{query}: expected {[expected_title]}, got {titles}"
    )

    assert all(
        resource.url.startswith("https://docs.python.org/3/")
        for resource in resources
    )

    print(f"PASS: {query} -> {expected_title}")


print("\n========== UNSUPPORTED TOPICS ==========")

for query in [
    "Python",
    "Python quantum computing",
    "Python blockchain",
]:
    resources = retriever.search(
        concept_name=query,
        max_results=10,
    )

    assert resources == [], (
        f"Unexpected documentation for {query}: {resources}"
    )

    print(f"PASS: {query} -> no unsupported recommendations")


print("\n========== INPUT VALIDATION ==========")

try:
    retriever.search(concept_name="", max_results=10)
    raise AssertionError("Empty concept was accepted.")
except ValueError:
    print("PASS: Empty concept rejected")

try:
    retriever.search(concept_name="Python recursion", max_results=0)
    raise AssertionError("Invalid max_results was accepted.")
except ValueError:
    print("PASS: Invalid max_results rejected")


print("\nSTEP 37 ALL TESTS PASSED")
