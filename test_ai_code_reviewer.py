import json
from types import SimpleNamespace

from app.coding_agent.ai_code_reviewer import AICodeReviewer


class FakeModels:
    def __init__(self, response_text):
        self.response_text = response_text
        self.calls = 0
        self.last_prompt = ""

    def generate_content(self, model, contents):
        self.calls += 1
        self.last_prompt = contents
        return SimpleNamespace(text=self.response_text)


class FakeClient:
    def __init__(self, response_text):
        self.models = FakeModels(response_text)


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"PASS: {name}")


student_code = (
    "def factorial(n):\n"
    "    if n == 1:\n"
    "        return 1\n"
    "    return n * factorial(n + 1)"
)

corrected_code = (
    "def factorial(n):\n"
    "    if n <= 1:\n"
    "        return 1\n"
    "    return n * factorial(n - 1)"
)

valid_response = json.dumps({
    "summary": "The recursive argument moves away from the base case.",
    "issues": [
        {
            "category": "logical_error",
            "explanation": "Increasing n prevents convergence to the base case.",
            "hint": "Think about whether n should increase or decrease.",
            "suggested_fix": "Replace n + 1 with n - 1.",
            "line_number": 4
        }
    ],
    "corrected_code": corrected_code,
    "learning_concept": "Recursion"
})


# TEST 1: Valid structured review
client = FakeClient(valid_response)
reviewer = AICodeReviewer(client=client)

result = reviewer.review(
    code=student_code,
    problem_description="Calculate factorial for non-negative integers.",
    concept_name="Recursion",
)

check(
    "Structured review parsed",
    result.summary != ""
    and len(result.issues) == 1
    and result.issues[0].category == "logical_error"
    and result.issues[0].line_number == 4,
)


# TEST 2: Corrected code is returned but NOT verified
check(
    "Correction remains unverified",
    result.corrected_code == corrected_code
    and result.correction_verified is False,
)


# TEST 3: Student code and structural evidence reach the reviewer
check(
    "Student code included in review prompt",
    student_code in client.models.last_prompt
    and "syntax_valid" in client.models.last_prompt
    and client.models.calls == 1,
)


# TEST 4: Empty submissions are rejected without an API call
empty_client = FakeClient(valid_response)
empty_reviewer = AICodeReviewer(client=empty_client)

try:
    empty_reviewer.review("   ")
except ValueError:
    empty_rejected = True
else:
    empty_rejected = False

check(
    "Empty submission rejected",
    empty_rejected and empty_client.models.calls == 0,
)


# TEST 5: Invalid JSON is rejected
invalid_reviewer = AICodeReviewer(
    client=FakeClient("This is not JSON.")
)

try:
    invalid_reviewer.review(student_code)
except ValueError:
    invalid_json_rejected = True
else:
    invalid_json_rejected = False

check(
    "Invalid JSON rejected",
    invalid_json_rejected,
)


# TEST 6: Invalid issue format is rejected
bad_issue_response = json.dumps({
    "summary": "Review",
    "issues": "This should have been a list.",
    "corrected_code": "",
    "learning_concept": "Recursion"
})

bad_issue_reviewer = AICodeReviewer(
    client=FakeClient(bad_issue_response)
)

try:
    bad_issue_reviewer.review(student_code)
except ValueError:
    bad_issue_rejected = True
else:
    bad_issue_rejected = False

check(
    "Malformed issues rejected",
    bad_issue_rejected,
)


# TEST 7: Markdown-fenced JSON is accepted
fenced_response = "```json\n" + valid_response + "\n```"

fenced_reviewer = AICodeReviewer(
    client=FakeClient(fenced_response)
)

fenced_result = fenced_reviewer.review(student_code)

check(
    "Markdown-fenced JSON parsed",
    fenced_result.learning_concept == "Recursion"
    and len(fenced_result.issues) == 1,
)


# TEST 8: Invalid line numbers are rejected
bad_line_response = json.dumps({
    "summary": "Review",
    "issues": [
        {
            "category": "logical_error",
            "explanation": "Example",
            "hint": "Example",
            "suggested_fix": "Example",
            "line_number": -5
        }
    ],
    "corrected_code": "",
    "learning_concept": "Recursion"
})

bad_line_reviewer = AICodeReviewer(
    client=FakeClient(bad_line_response)
)

try:
    bad_line_reviewer.review(student_code)
except ValueError:
    bad_line_rejected = True
else:
    bad_line_rejected = False

check(
    "Invalid line number rejected",
    bad_line_rejected,
)


print("\nALL EIGHT AI CODE REVIEW TESTS PASSED.")
