from dataclasses import dataclass

from app.coding_agent.models import CodingTask


@dataclass(frozen=True)
class ProgressiveHint:
    concept_name: str
    level: int
    title: str
    message: str
    misconception_target: str = ""
    reveals_solution: bool = False


class ProgressiveHintEngine:
    """
    Provides progressively more specific educational hints.

    This engine does not execute student code, submit assessment
    evidence, or modify the shared CACM cognitive model.

    The current hint bank supports the verified introductory
    exercises for Recursion, Prime Numbers, and Arrays.
    """

    HINT_BANK = {
        "Recursion": [
            (
                "Think about when to stop",
                "Every recursive function needs a condition that "
                "stops it from calling itself. What is the smallest "
                "input whose answer you already know?",
            ),
            (
                "Identify the base case",
                "For factorial, consider what factorial(0) should "
                "return. Your function should handle this before "
                "making another recursive call.",
            ),
            (
                "Structure the recursive solution",
                "First handle the base case with a conditional. "
                "Otherwise, return n multiplied by factorial(n - 1).",
            ),
        ],
        "Prime Numbers": [
            (
                "Think about divisibility",
                "A prime number has exactly two positive divisors: "
                "1 and itself. Which inputs should immediately "
                "return False?",
            ),
            (
                "Check possible divisors",
                "Numbers less than 2 are not prime. For other "
                "numbers, check whether a smaller integer divides "
                "the number without a remainder.",
            ),
            (
                "Improve the divisor search",
                "Try checking candidate divisors from 2 up to "
                "the square root of the input. If any divides "
                "evenly, return False; otherwise return True.",
            ),
        ],
        "Arrays": [
            (
                "Think about the running answer",
                "You can find the largest element by keeping "
                "track of the biggest value seen so far.",
            ),
            (
                "Choose an initial value",
                "Consider initializing the running maximum using "
                "the first element rather than assuming all "
                "numbers are positive.",
            ),
            (
                "Update while traversing",
                "Loop through the remaining elements. Whenever "
                "an element exceeds the running maximum, update "
                "it. Return the maximum after the loop.",
            ),
        ],
    }

    def __init__(self):
        self._request_counts = {}

    @staticmethod
    def _validate_task(task: CodingTask):
        if not isinstance(task, CodingTask):
            raise TypeError("task must be a CodingTask.")

        if task.concept_name not in ProgressiveHintEngine.HINT_BANK:
            raise ValueError(
                "No verified progressive hints are available "
                f"for {task.concept_name}."
            )

    def get_hint(
        self,
        task: CodingTask,
        level: int,
        misconception: str = "",
    ) -> ProgressiveHint:
        self._validate_task(task)

        if not isinstance(level, int) or isinstance(level, bool):
            raise TypeError("Hint level must be an integer.")

        if level not in {1, 2, 3}:
            raise ValueError("Hint level must be 1, 2, or 3.")

        if not isinstance(misconception, str):
            raise TypeError("misconception must be a string.")

        title, message = self.HINT_BANK[task.concept_name][level - 1]

        target = misconception.strip()

        if target and task.misconception_targets:
            normalized_targets = {
                item.strip().lower()
                for item in task.misconception_targets
            }

            if target.lower() not in normalized_targets:
                target = ""

        return ProgressiveHint(
            concept_name=task.concept_name,
            level=level,
            title=title,
            message=message,
            misconception_target=target,
            reveals_solution=False,
        )

    def get_next_hint(
        self,
        task: CodingTask,
        session_id: str,
        misconception: str = "",
    ) -> ProgressiveHint:
        self._validate_task(task)

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id cannot be empty.")

        key = (
            session_id.strip(),
            task.concept_name,
            task.title,
        )

        previous = self._request_counts.get(key, 0)
        next_level = min(previous + 1, 3)

        hint = self.get_hint(
            task=task,
            level=next_level,
            misconception=misconception,
        )

        self._request_counts[key] = next_level

        return hint

    def reset_hints(self, task: CodingTask, session_id: str):
        self._validate_task(task)

        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id cannot be empty.")

        key = (
            session_id.strip(),
            task.concept_name,
            task.title,
        )

        self._request_counts.pop(key, None)
