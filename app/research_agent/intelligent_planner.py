from __future__ import annotations

from dataclasses import dataclass, field

from app.cognitive.models import StudentCognitiveModel
from app.research_agent.agent import ResearchAgent, ResearchAction


@dataclass
class ResearchPlan:
    topic: str
    concept_name: str
    action: ResearchAction
    is_new_concept: bool
    research_goal: str
    search_queries: list[str] = field(default_factory=list)
    analysis_focus: list[str] = field(default_factory=list)
    planning_reason: str = ""


class IntelligentResearchPlanner:
    """
    Builds a state-aware research plan before paper retrieval.

    Planning does not modify the student's cognitive state.
    """

    def __init__(self, research_agent=None):
        self.research_agent = research_agent or ResearchAgent()

    def create_plan(
        self,
        student: StudentCognitiveModel,
        topic: str,
        concept_name: str,
        has_active_conflict: bool = False,
    ) -> ResearchPlan:

        topic = topic.strip()
        concept_name = concept_name.strip()

        if not topic:
            raise ValueError("Research topic cannot be empty.")

        if not concept_name:
            raise ValueError("Learning concept cannot be empty.")

        state = student.get_concept(concept_name)

        is_new = state.attempts == 0

        if has_active_conflict:

            action = self.research_agent.choose_action(
                student=student,
                concept_name=concept_name,
                has_active_conflict=True,
            )

            goal = (
                "Investigate the concept using targeted research "
                "to support a diagnostic comprehension assessment."
            )

            focus = [
                "Core conceptual explanations",
                "Commonly reported challenges and limitations",
                "Evidence relevant to diagnostic assessment",
            ]

            reason = (
                "CACM reported conflicting evidence. "
                "Diagnostic research takes priority."
            )

        elif is_new:

            action = ResearchAction(
                action_type="introductory_research",
                concept_name=concept_name,
                difficulty="easy",
                reason=(
                    "This concept has no recorded assessment attempts. "
                    "Start with introductory research without assuming "
                    "the student's initial mastery estimate is measured knowledge."
                ),
            )

            goal = (
                "Introduce the topic using accessible, "
                "source-supported research findings."
            )

            focus = [
                "Foundational concepts",
                "Main research approaches",
                "Clearly reported findings and limitations",
            ]

            reason = (
                "The concept is unassessed. "
                "An introductory research plan is appropriate."
            )

        else:

            action = self.research_agent.choose_action(
                student=student,
                concept_name=concept_name,
                has_active_conflict=False,
            )

            focus_by_action = {
                "foundational_research": [
                    "Foundational explanations",
                    "Basic methodologies",
                    "Accessible examples from available sources",
                ],
                "guided_research": [
                    "Main research methodologies",
                    "Comparison of reported approaches",
                    "Reported findings and limitations",
                ],
                "verification_research": [
                    "Methodological differences",
                    "Evidence needed to verify understanding",
                    "Reported evaluation methods",
                ],
                "advanced_research": [
                    "Methodological comparison",
                    "Reported limitations",
                    "Potential research directions requiring verification",
                ],
            }

            focus = focus_by_action.get(
                action.action_type,
                ["Source-supported research findings"],
            )

            goal = (
                "Conduct research appropriate to the student's "
                "current assessed cognitive state."
            )

            reason = action.reason

        queries = [topic]

        if action.action_type in {
            "introductory_research",
            "foundational_research",
        }:
            queries.append(f"{topic} review")

        elif action.action_type == "diagnostic_research":
            queries.append(f"{topic} challenges and limitations")

        elif action.action_type in {
            "verification_research",
            "advanced_research",
        }:
            queries.append(f"{topic} methods evaluation")

        else:
            queries.append(f"{topic} comparative study")

        return ResearchPlan(
            topic=topic,
            concept_name=concept_name,
            action=action,
            is_new_concept=is_new,
            research_goal=goal,
            search_queries=queries,
            analysis_focus=focus,
            planning_reason=reason,
        )
