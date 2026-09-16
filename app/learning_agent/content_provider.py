from abc import ABC, abstractmethod

from app.learning_agent.content_generator import GeneratedContent


class ContentProvider(ABC):
    """
    Interface for any system capable of producing
    actual educational content.

    Possible implementations:
    - Gemini
    - another LLM
    - local model
    - rule/template system

    The cognitive architecture therefore does not
    depend directly on a specific LLM.
    """

    @abstractmethod
    def create_content(
        self,
        request: GeneratedContent,
    ) -> str:
        pass


class LocalContentProvider(ContentProvider):
    """
    Temporary local provider used before connecting
    an external LLM.

    It converts the personalized request into simple
    usable educational content.
    """

    def create_content(
        self,
        request: GeneratedContent,
    ) -> str:

        concept = request.concept_name

        if request.content_type == "teach_concept":
            return (
                f"{concept} is being introduced at a "
                f"{request.difficulty} level. "
                f"Start by understanding the basic idea, "
                f"then study a simple worked example."
            )

        if request.content_type == "practice_quiz":
            return (
                f"Practice Question ({request.difficulty}):\n"
                f"Explain how {concept} works and give "
                f"one example where it can be applied."
            )

        if request.content_type == "diagnostic_quiz":
            return (
                f"Diagnostic Question:\n"
                f"Without using a memorized definition, "
                f"explain {concept} using your own example."
            )

        if request.content_type == "verification_quiz":
            return (
                f"Verification Question ({request.difficulty}):\n"
                f"Solve a challenging problem involving "
                f"{concept} and explain your reasoning."
            )

        if request.content_type == "advance_topic":
            return (
                f"You are ready to explore a more advanced "
                f"application related to {concept}."
            )

        raise ValueError(
            f"Unsupported content type: "
            f"{request.content_type}"
        )