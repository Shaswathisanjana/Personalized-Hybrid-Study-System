from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.cognitive.misconception_tracker import (
    MisconceptionHypothesis,
    MisconceptionTracker,
)


class CognitiveMisconceptionManager:
    """
    Manages misconception hypotheses stored inside
    the shared StudentCognitiveModel.
    """

    def __init__(self):
        self.tracker = MisconceptionTracker()


    # ==================================================
    # RECORD SUPPORT
    # ==================================================

    def record_support(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        description: str,
        source_agent: str,
    ) -> MisconceptionHypothesis:
        """
        Records evidence supporting a misconception.

        If the misconception has never been observed,
        a new hypothesis is created.

        Otherwise, the existing hypothesis is
        strengthened.
        """

        concept = student.get_concept(
            concept_name
        )

        description = description.strip()

        if not description:
            raise ValueError(
                "Misconception description cannot be empty."
            )


        # ----------------------------------------------
        # CREATE NEW HYPOTHESIS
        # ----------------------------------------------

        if (
            description
            not in concept.misconception_hypotheses
        ):

            hypothesis = (
                self.tracker.create_hypothesis(
                    description=description,
                    source_agent=source_agent,
                )
            )

            concept.misconception_hypotheses[
                description
            ] = hypothesis


        # ----------------------------------------------
        # UPDATE EXISTING HYPOTHESIS
        # ----------------------------------------------

        else:

            hypothesis = (
                concept.misconception_hypotheses[
                    description
                ]
            )

            self.tracker.add_support(
                hypothesis=hypothesis,
                source_agent=source_agent,
            )


        self._sync_legacy_misconceptions(
            student=student,
            concept_name=concept_name,
        )

        return hypothesis


    # ==================================================
    # RECORD CONTRADICTION
    # ==================================================

    def record_contradiction(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        description: str,
        source_agent: str,
    ) -> MisconceptionHypothesis:
        """
        Records evidence against an existing
        misconception hypothesis.
        """

        concept = student.get_concept(
            concept_name
        )

        description = description.strip()


        if (
            description
            not in concept.misconception_hypotheses
        ):
            raise ValueError(
                "Cannot contradict a misconception "
                "hypothesis that does not exist."
            )


        hypothesis = (
            concept.misconception_hypotheses[
                description
            ]
        )


        self.tracker.add_contradiction(
            hypothesis=hypothesis,
            source_agent=source_agent,
        )


        self._sync_legacy_misconceptions(
            student=student,
            concept_name=concept_name,
        )


        return hypothesis


    # ==================================================
    # GET HYPOTHESIS
    # ==================================================

    def get_hypothesis(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        description: str,
    ) -> MisconceptionHypothesis | None:

        concept = student.get_concept(
            concept_name
        )

        return (
            concept.misconception_hypotheses.get(
                description
            )
        )


    # ==================================================
    # SYNCHRONIZE OLD LIST
    # ==================================================

    def _sync_legacy_misconceptions(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> None:
        """
        Keeps the old list[str] representation
        synchronized with structured hypotheses.

        Only ACTIVE hypotheses are exposed through
        the legacy list.

        This allows older components such as the
        content generator to continue working.
        """

        concept = student.get_concept(
            concept_name
        )


        concept.misconceptions = [
            hypothesis.description
            for hypothesis
            in concept.misconception_hypotheses.values()
            if hypothesis.status == "active"
        ]
        