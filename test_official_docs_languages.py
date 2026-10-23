from app.learning_agent.resources.official_docs_retriever import (
    OfficialDocumentationRetriever,
)

retriever = OfficialDocumentationRetriever()

print("\n========== CROSS-LANGUAGE DOCUMENTATION TEST ==========")

rejected_queries = [
    "Java recursion",
    "C recursion",
    "C++ recursion",
    "C# recursion",
    "JavaScript recursion",
    "Ruby recursion",
    "Rust recursion",
    "Kotlin recursion",
    "Python and Java recursion",
]

for query in rejected_queries:
    results = retriever.search(
        concept_name=query,
        max_results=10,
        target_level="easy",
    )

    assert results == [], (
        f"Incorrect Python documentation returned for {query}: "
        f"{[r.title for r in results]}"
    )

    print(f"PASS: {query} -> rejected")


print("\n========== VALID PYTHON QUERIES ==========")

valid_queries = [
    "Python recursion",
    "Python lists",
    "Python exceptions",
    "Python functions",
]

for query in valid_queries:
    results = retriever.search(
        concept_name=query,
        max_results=10,
        target_level="easy",
    )

    assert len(results) >= 1, (
        f"Expected Python documentation for {query}"
    )

    assert all(
        r.source == "Official Python Documentation"
        for r in results
    )

    print(
        f"PASS: {query} -> "
        f"{[r.title for r in results]}"
    )


print("\nSTEP 39 ALL CROSS-LANGUAGE TESTS PASSED")
