from app.learning_agent.resources.models import LearningResource
from app.learning_agent.resources.relevance_guard import ResourceRelevanceGuard

guard = ResourceRelevanceGuard()


def resource(title, description="", source="YouTube"):
    return LearningResource(
        title=title,
        url="https://example.com/test",
        resource_type="article",
        description=description,
        source=source,
    )


cases = [
    # Query-topic matching
    ("Python recursion",
     resource("Complete Python Installation Guide"), False),

    ("Python recursion",
     resource("Recursive Functions Explained in Python"), True),

    ("Python recursion",
     resource("Recursion Tutorial in Java"), False),

    # Programming-language distinctions
    ("Python recursion",
     resource("Recursion in C++"), False),

    ("Python recursion",
     resource("Recursion in C#"), False),

    ("C++ recursion",
     resource("Recursion in C++ for Beginners"), True),

    ("C# recursion",
     resource("Recursion in C# Explained"), True),

    ("C recursion",
     resource("Recursion in C Programming"), True),

    ("C recursion",
     resource("Recursion in C++"), False),

    # Language-only queries
    ("Python",
     resource("Python Programming for Beginners"), True),

    ("Python",
     resource("Introduction to Java Programming"), False),

    # General educational concepts
    ("Binary Search",
     resource("Binary Search Algorithm Tutorial"), True),

    ("Binary Search",
     resource("Neural Network Architecture"), False),

    ("Machine Learning",
     resource("Introduction to Machine Learning"), True),

    # Wikipedia filtering
    ("Recursion",
     resource("Recursion (Crouch novel)", source="Wikipedia"), False),

    ("Recursion",
     resource("Recursion (computer science)", source="Wikipedia"), True),

    ("Recursion",
     resource("Recursion (disambiguation)", source="Wikipedia"), False),
]

print("\n========== EXTENDED RELEVANCE TEST ==========")

failures = []

for index, (query, candidate, expected) in enumerate(cases, 1):
    actual = guard.is_relevant(query, candidate)
    passed = actual == expected

    print(
        f"{index:02d}. {'PASS' if passed else 'FAIL'} | "
        f"{query} | {candidate.title} | "
        f"Expected={expected}, Actual={actual}"
    )

    if not passed:
        failures.append(index)

print(f"\nPassed: {len(cases) - len(failures)}/{len(cases)}")

if failures:
    print("Failed cases:", failures)
    raise SystemExit(1)

print("\nSTEP 27 TEST PASSED")
