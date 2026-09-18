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
    Local fallback content provider.

    This provider allows the Learning Agent and CACM
    pipeline to continue functioning without depending
    on an external LLM.

    It supports every pedagogical content type currently
    used by the Learning Agent.
    """

    def create_content(
        self,
        request: GeneratedContent,
    ) -> str:

        concept = request.concept_name

        # ==================================================
        # TEACH CONCEPT
        # ==================================================

        if request.content_type == "teach_concept":

            return (
                f"{concept} is being introduced at a "
                f"{request.difficulty} level. "
                f"Start by understanding the basic idea, "
                f"then study a simple worked example."
            )

        # ==================================================
        # PRACTICE
        # ==================================================

        if request.content_type == "practice_quiz":

            return (
                f"Practice Question "
                f"({request.difficulty}):\n"
                f"Explain how {concept} works and give "
                f"one example where it can be applied."
            )

        # ==================================================
        # DIAGNOSTIC ASSESSMENT
        # ==================================================

        if request.content_type == "diagnostic_quiz":

            return (
                f"Diagnostic Question:\n"
                f"Without using a memorized definition, "
                f"explain {concept} using your own example."
            )

        # ==================================================
        # VERIFICATION ASSESSMENT
        # ==================================================

        if request.content_type == "verification_quiz":

            return (
                f"Verification Question "
                f"({request.difficulty}):\n"
                f"Solve a challenging problem involving "
                f"{concept} and explain your reasoning."
            )

        # ==================================================
        # TARGETED REMEDIATION
        # ==================================================

        if request.content_type == "targeted_remediation":

            return (
                f"Let's revisit {concept} at a "
                f"{request.difficulty} level.\n\n"
                f"Your recent answer suggests that one "
                f"part of this concept may need more "
                f"clarification.\n\n"
                f"Review the key idea carefully using a "
                f"simpler explanation and worked example "
                f"before attempting another question."
            )

        # ==================================================
        # ADVANCE TOPIC
        # ==================================================

        if request.content_type == "advance_topic":

            return (
                f"You are ready to explore a more "
                f"advanced application related to "
                f"{concept}."
            )

        # ==================================================
        # UNKNOWN CONTENT TYPE
        # ==================================================

        raise ValueError(
            f"Unsupported content type: "
            f"{request.content_type}"
        )