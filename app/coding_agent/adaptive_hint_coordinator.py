from dataclasses import dataclass

from app.coding_agent.models import CodingTask
from app.coding_agent.misconception_detector import (
    CodingMisconceptionDetector,
    PossibleMisconception,
)
from app.coding_agent.progressive_hint_engine import (
    ProgressiveHint,
    ProgressiveHintEngine,
)


@dataclass(frozen=True)
class AdaptiveHintResult:
    hint: ProgressiveHint
    is_targeted: bool
    detected_issue: PossibleMisconception | None = None
    analysis_message: str = ""


class MisconceptionAwareHintCoordinator:
    """
    Connects code-pattern analysis with progressive hints.

    Does not execute student code, evaluate submissions,
    or update the CACM cognitive model.
    """

    def __init__(
        self,
        detector=None,
        hint_engine=None,
    ):
        self.detector = (
            detector or CodingMisconceptionDetector()
        )
        self.hint_engine = (
            hint_engine or ProgressiveHintEngine()
        )

    def get_next_hint(
        self,
        task: CodingTask,
        code: str,
        session_id: str,
    ) -> AdaptiveHintResult:
        if not isinstance(task, CodingTask):
            raise TypeError("task must be a CodingTask.")

        if not isinstance(code, str):
            raise TypeError("code must be a string.")

        # Advance the curated hint progression exactly once.
        base_hint = self.hint_engine.get_next_hint(
            task=task,
            session_id=session_id,
        )

        analysis = self.detector.analyze(
            task=task,
            code=code,
        )

        if (
            base_hint.level == 1
            and analysis.syntax_valid
            and analysis.findings
        ):
            finding = analysis.findings[0]

            targeted_hint = ProgressiveHint(
                concept_name=task.concept_name,
                level=1,
                title="A possible issue in your code",
                message=finding.targeted_hint,
                misconception_target=finding.code,
                reveals_solution=False,
            )

            return AdaptiveHintResult(
                hint=targeted_hint,
                is_targeted=True,
                detected_issue=finding,
                analysis_message=analysis.message,
            )

        return AdaptiveHintResult(
            hint=base_hint,
            is_targeted=False,
            detected_issue=None,
            analysis_message=analysis.message,
        )

    def reset_hints(
        self,
        task: CodingTask,
        session_id: str,
    ):
        self.hint_engine.reset_hints(
            task=task,
            session_id=session_id,
        )
