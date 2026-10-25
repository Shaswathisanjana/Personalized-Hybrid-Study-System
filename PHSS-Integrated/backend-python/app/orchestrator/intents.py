"""Explicit intents which do not need a remote model to choose a workspace."""
import re

def explicit_intent(message):
    q = message.lower()
    if normalize_learning_topic(message) != message.strip():
        return 'learning'
    practice = re.search(r'\b(practi[cs]e|practice|solve|questions?|problems?|interview|leetcode)\b', q)
    company = re.search(r'\b(amazon|google|microsoft|meta|apple|infosys|tcs|accenture|walmart|zoho)\b', q)
    coding = re.search(r'\b(dsa|coding|algorithms?|data structures|leetcode)\b', q)
    learning = re.search(r'\b(learn|learning|teach|understand|roadmap|study|improve)\b', q)
    if practice and (company or coding) and not learning:
        return 'coding'
    if learning and not re.search(r'\b(debug|implement|research papers|find papers)\b', q):
        return 'learning'
    return None

def is_practice_request(message):
    return explicit_intent(message) == 'coding'

def normalize_learning_topic(topic):
    # Bare trees in this study workspace means DSA; explicit biology stays biology.
    value = topic.strip()
    stripped = re.sub(r"^(?:(?:i\s+)?(?:want(?:ed)?\s+to\s+)?(?:learn|study|understand)|teach\s+me|explain)\s+", "", value, flags=re.I).strip(" .?!")
    stripped = re.sub(r"^i\s+want(?:ed)?\s+(?:to\s+learn\s+)?", "", stripped, flags=re.I)
    if stripped.lower() in {"tree", "trees", "trees in dsa", "tree data structure"}:
        return "Trees in Data Structures and Algorithms"
    return value
