"""Conservative concept identities shared by all agents.

Names remain suitable for display. IDs are for equality and dictionary keys.
Only the explicit aliases below merge differently worded topics; no substring,
LLM, stemming, punctuation stripping, or language-prefix guesses are used.
"""

IDENTITY_VERSION = 1
ALIASES = {
    "python recursion": "recursion",
    "recursion in python": "recursion",
    "prime number": "prime numbers",
    "prime": "prime numbers",
    "array": "arrays",
}


def clean_concept_name(name: str) -> str:
    if not isinstance(name, str):
        raise TypeError("Concept name must be a string.")
    cleaned = " ".join(name.split())
    if not cleaned:
        raise ValueError("Concept name cannot be empty.")
    return cleaned


def concept_id(name: str) -> str:
    normalized = clean_concept_name(name).casefold()
    return ALIASES.get(normalized, normalized)
