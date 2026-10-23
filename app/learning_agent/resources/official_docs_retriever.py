from app.learning_agent.resources.models import LearningResource
from app.learning_agent.resources.difficulty_estimator import (
    ResourceDifficultyEstimator,
)


class OfficialDocumentationRetriever:
    """
    Retrieve resources from an explicitly curated catalogue
    of official documentation pages.

    This initial implementation supports Python topics.
    It does not invent URLs or claim to search the entire web.
    """

    DOCUMENTATION = [
        {
            "title": "Python Tutorial - Defining Functions",
            "url": "https://docs.python.org/3/tutorial/controlflow.html#defining-functions",
            "description": (
                "Official Python tutorial covering function definitions, "
                "parameters, arguments, and function behaviour."
            ),
            "keywords": {
                "python", "functions", "function",
                "parameters", "arguments",
            },
        },
        {
            "title": "Python Tutorial - Data Structures",
            "url": "https://docs.python.org/3/tutorial/datastructures.html",
            "description": (
                "Official Python tutorial covering lists, tuples, "
                "sets, dictionaries, and common data structures."
            ),
            "keywords": {
                "python", "list", "lists", "tuple", "tuples",
                "set", "sets", "dictionary", "dictionaries",
                "data structures",
            },
        },
        {
            "title": "Python Tutorial - Control Flow Tools",
            "url": "https://docs.python.org/3/tutorial/controlflow.html",
            "description": (
                "Official Python tutorial explaining if statements, "
                "for loops, while loops, and control flow."
            ),
            "keywords": {
                "python", "control flow", "loops", "loop",
                "for", "while", "if", "conditions",
            },
        },
        {
            "title": "Python Tutorial - Errors and Exceptions",
            "url": "https://docs.python.org/3/tutorial/errors.html",
            "description": (
                "Official Python documentation covering exception "
                "handling, errors, try, except, and raising exceptions."
            ),
            "keywords": {
                "python", "exception", "exceptions",
                "errors", "error", "try", "except",
            },
        },
        {
            "title": "Python Standard Library - functools",
            "url": "https://docs.python.org/3/library/functools.html",
            "description": (
                "Official Python reference for higher-order functions, "
                "caching, and tools useful for recursive functions."
            ),
            "keywords": {
                "python", "recursion", "recursive",
                "memoization", "caching", "functools",
            },
        },
    ]

    def __init__(self, difficulty_estimator=None):
        self.difficulty_estimator = (
            difficulty_estimator
            if difficulty_estimator is not None
            else ResourceDifficultyEstimator()
        )

    def search(
        self,
        concept_name,
        max_results=10,
        target_level=None,
    ):
        if not isinstance(concept_name, str) or not concept_name.strip():
            raise ValueError("concept_name cannot be empty.")

        if max_results <= 0:
            raise ValueError("max_results must be greater than zero.")

        query = concept_name.lower().strip()
        query_words = set(query.replace("-", " ").split())

        # This catalogue contains Python documentation only.
        # Do not recommend it for another requested language.
        from app.learning_agent.resources.relevance_guard import (
            ResourceRelevanceGuard,
        )

        requested_languages = (
            ResourceRelevanceGuard._mentioned_languages(query)
        )

        if requested_languages and requested_languages != {"python"}:
            return []

        # "Python" establishes the documentation context,
        # but is not sufficient evidence of topic relevance.
        topic_words = query_words - {"python"}

        if not topic_words:
            return []

        candidates = []

        for entry in self.DOCUMENTATION:
            keyword_matches = 0

            for keyword in entry["keywords"]:
                keyword_words = set(keyword.split())

                # Ignore generic language-only matches.
                if keyword_words == {"python"}:
                    continue

                if keyword_words.issubset(topic_words):
                    keyword_matches += len(keyword_words)

            if keyword_matches == 0:
                continue

            difficulty = self.difficulty_estimator.estimate(
                title=entry["title"],
                description=entry["description"],
            )

            resource = LearningResource(
                title=entry["title"],
                url=entry["url"],
                resource_type="documentation",
                description=entry["description"],
                source="Official Python Documentation",
                difficulty=difficulty,
                topics=[],
            )

            candidates.append((keyword_matches, resource))

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            resource
            for _, resource in candidates[:max_results]
        ]


