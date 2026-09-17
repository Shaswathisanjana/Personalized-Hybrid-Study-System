import json
import os

from dotenv import load_dotenv
from google import genai

from app.coding_agent.models import CodingTask


load_dotenv()


class CodingTaskGenerator:
    """
    Generates coding tasks for a specific concept
    and difficulty.

    Gemini generates the educational content, while
    Python validates the returned structure before
    creating a CodingTask.
    """

    VALID_DIFFICULTIES = {
        "easy",
        "medium",
        "hard",
    }

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
    ):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found in the environment."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model_name = model_name

    def generate(
        self,
        concept_name: str,
        difficulty: str,
    ) -> CodingTask:
        """
        Generate one coding task.

        Parameters
        ----------
        concept_name:
            Concept that the task should evaluate.

        difficulty:
            easy, medium, or hard.
        """

        concept_name = concept_name.strip()

        difficulty = (
            difficulty.strip().lower()
        )

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if difficulty not in self.VALID_DIFFICULTIES:
            raise ValueError(
                "difficulty must be easy, medium, or hard."
            )

        prompt = f"""
You are generating ONE programming task for an
educational Coding Agent.

Concept:
{concept_name}

Difficulty:
{difficulty}

The purpose of this task is to collect evidence about
whether a student understands the given programming
concept.

Requirements:

1. The task must directly test the concept:
   {concept_name}

2. Difficulty must be appropriate for:
   {difficulty}

3. The task should be solvable in Python.

4. The task description must clearly explain what the
   student needs to implement.

5. Provide starter code containing the function
   signature when appropriate.

6. Do NOT provide the complete solution.

7. expected_behavior should describe what a correct
   program/function should do without giving the
   implementation.

8. misconception_targets must contain possible
   conceptual misunderstandings that this task could
   reveal.

9. Do not claim that the student has any misconception.
   These are only POSSIBLE targets. Actual
   misconceptions will be determined from the
   student's submitted code.

Return ONLY valid JSON in exactly this format:

{{
    "title": "short task title",
    "description": "clear programming task",
    "starter_code": "Python starter code",
    "expected_behavior": "description of correct behavior",
    "misconception_targets": [
        "possible misconception 1",
        "possible misconception 2"
    ]
}}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        raw_text = response.text.strip()

        # Gemini may occasionally wrap JSON inside
        # Markdown fences. Remove them safely.
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            raw_text = "\n".join(lines).strip()

            if raw_text.startswith("json"):
                raw_text = raw_text[4:].strip()

        try:
            data = json.loads(raw_text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Coding task generator returned invalid JSON."
            ) from exc

        title = str(
            data.get(
                "title",
                "",
            )
        ).strip()

        description = str(
            data.get(
                "description",
                "",
            )
        ).strip()

        starter_code = str(
            data.get(
                "starter_code",
                "",
            )
        )

        expected_behavior = str(
            data.get(
                "expected_behavior",
                "",
            )
        ).strip()

        misconception_targets = data.get(
            "misconception_targets",
            [],
        )

        if not isinstance(
            misconception_targets,
            list,
        ):
            misconception_targets = []

        misconception_targets = [
            str(item).strip()
            for item in misconception_targets
            if str(item).strip()
        ]

        if not title:
            raise ValueError(
                "Generated coding task has no title."
            )

        if not description:
            raise ValueError(
                "Generated coding task has no description."
            )

        if not expected_behavior:
            raise ValueError(
                "Generated coding task has no expected behavior."
            )

        return CodingTask(
            concept_name=concept_name,
            title=title,
            description=description,
            difficulty=difficulty,
            starter_code=starter_code,
            expected_behavior=expected_behavior,
            misconception_targets=misconception_targets,
        )