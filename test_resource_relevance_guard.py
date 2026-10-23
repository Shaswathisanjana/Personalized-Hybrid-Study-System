from app.learning_agent.resources.models import LearningResource
from app.learning_agent.resources.relevance_guard import ResourceRelevanceGuard

guard = ResourceRelevanceGuard()


def make_resource(title, description="", source="YouTube"):
    return LearningResource(
        title=title,
        url="https://example.com/test",
        resource_type="article",
        description=description,
        source=source,
    )


cases = [
    (
        "Python recursion",
        make_resource("Python Recursion Tutorial for Beginners"),
        True,
    ),
    (
        "Python recursion",
        make_resource("Recursion in Java Full Tutorial"),
        False,
    ),
    (
        "Python recursion",
        make_resource("Recursion in C Programming"),
        False,
    ),
    (
        "Python recursion",
        make_resource("Understanding Recursive Functions in Python"),
        True,
    ),
    (
        "Recursion",
        make_resource(
            "Recursion (Crouch novel)",
            source="Wikipedia",
        ),
        False,
    ),
    (
        "Recursion",
        make_resource(
            "Recursion (computer science)",
            source="Wikipedia",
        ),
        True,
    ),
    (
        "Binary Search",
        make_resource("Binary Search Explained with Examples"),
        True,
    ),
    (
        "Binary Search",
        make_resource("Introduction to Neural Networks"),
        False,
    ),
    (
        "Machine Learning",
        make_resource("Machine Learning Fundamentals"),
        True,
    ),
]

print("\n========== RELEVANCE GUARD TEST ==========")

failures = []

for index, (query, resource, expected) in enumerate(cases, start=1):
    actual = guard.is_relevant(query, resource)
    passed = actual == expected

    print(
        f"{index}. {'PASS' if passed else 'FAIL'} | "
        f"Query: {query} | "
        f"Resource: {resource.title} | "
        f"Expected: {expected} | Actual: {actual}"
    )

    if not passed:
        failures.append(index)

print(f"\nPassed: {len(cases) - len(failures)}/{len(cases)}")

if failures:
    print("Failed cases:", failures)
    raise SystemExit(1)

print("\nSTEP 23 TEST PASSED")
