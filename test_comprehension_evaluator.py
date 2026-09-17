from app.research_agent.models import (
    ResearchComprehensionQuestion,
    ResearchStudentAnswer,
)

from app.research_agent.comprehension_evaluator import (
    ResearchComprehensionEvaluator,
)


# ==========================================================
# FIXED COMPREHENSION QUESTION
# ==========================================================

question = ResearchComprehensionQuestion(
    concept_name="recursion",

    question=(
        "If an instructor wants to improve a novice "
        "programmer's ability to grasp recursion, how "
        "should they adjust their instructional strategy, "
        "and why is this adjustment necessary?"
    ),

    correct_answer=(
        "The instructor should use concrete conceptual "
        "models rather than purely abstract models because "
        "recursion requires novices to trace non-linear "
        "and hierarchical execution."
    ),

    explanation=(
        "Recursion can be difficult because students must "
        "mentally trace non-linear and hierarchical "
        "execution. Concrete conceptual models can make "
        "this structure easier to understand."
    ),

    difficulty="medium",

    misconception_targets=[
        (
            "Recursion difficulty is only caused by "
            "programming syntax."
        ),
        (
            "Abstract and concrete teaching models are "
            "equally useful for novice understanding."
        ),
    ],
)


evaluator = (
    ResearchComprehensionEvaluator()
)


def run_case(
    case_name: str,
    answer_text: str,
):
    """
    Evaluate and display one student answer.
    """

    student_answer = (
        ResearchStudentAnswer(
            user_id="student_001",
            question=question,
            answer=answer_text,
        )
    )

    result = evaluator.evaluate(
        student_answer
    )

    print(
        f"\n========== {case_name} =========="
    )

    print(
        "Student answer:",
        answer_text,
    )

    print(
        "Correct:",
        result.is_correct,
    )

    print(
        "Performance:",
        result.performance,
    )

    print(
        "Confidence:",
        result.confidence,
    )

    print(
        "Feedback:",
        result.feedback,
    )

    print(
        "Detected misconceptions:",
        result.detected_misconceptions,
    )

    return result


# ==========================================================
# CASE A
#
# Correct meaning, but wording is intentionally different
# from the expected answer.
# ==========================================================

case_a = run_case(
    "CASE A - SEMANTICALLY CORRECT",

    (
        "The teacher should use something more concrete "
        "that lets beginners visualize how the nested "
        "execution moves through the calls instead of "
        "only explaining it abstractly."
    ),
)


# ==========================================================
# CASE B
#
# Student understands the teaching recommendation but
# gives an incomplete explanation of WHY.
# ==========================================================

case_b = run_case(
    "CASE B - PARTIAL UNDERSTANDING",

    (
        "The teacher should use concrete models instead "
        "of only abstract explanations because they are "
        "easier for beginners."
    ),
)


# ==========================================================
# CASE C
#
# Student demonstrates a misconception that recursion's
# difficulty is only about syntax.
# ==========================================================

case_c = run_case(
    "CASE C - MISCONCEPTION",

    (
        "The main problem is that recursion has difficult "
        "programming syntax. The teacher just needs to "
        "teach the syntax more clearly."
    ),
)


# ==========================================================
# VALIDATION
# ==========================================================

assert (
    case_a.performance
    >= 0.75
)

assert (
    case_a.is_correct
    is True
)


assert (
    0.0
    < case_b.performance
    < 1.0
)


assert (
    case_c.performance
    < 0.75
)

assert (
    case_c.is_correct
    is False
)


assert (
    len(
        case_c.detected_misconceptions
    )
    > 0
)


assert all(
    0.0
    <= result.confidence
    <= 1.0
    for result in [
        case_a,
        case_b,
        case_c,
    ]
)


print(
    "\n========== COMPREHENSION EVALUATOR TEST PASSED =========="
)

print(
    "The Research Agent distinguished semantic "
    "understanding, partial understanding, and "
    "misconception evidence."
)