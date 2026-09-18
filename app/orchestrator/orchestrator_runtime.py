from dataclasses import dataclass, field
from typing import Any

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.models import StudentCognitiveModel

from app.learning_agent.runtime import LearningAgentRuntime
from app.learning_agent.gemini_provider import GeminiContentProvider

from app.research_agent.paper_search import AcademicPaperSearch
from app.research_agent.semantic_ranker import SemanticPaperRanker
from app.research_agent.evidence_extractor import ResearchEvidenceExtractor
from app.research_agent.research_synthesizer import ResearchSynthesizer

from app.coding_agent.task_generator import CodingTaskGenerator

from app.orchestrator.query_router import (
    QueryRouter,
    QueryRoute,
)


@dataclass
class AgentExecutionResult:
    """
    Result produced by one specialized agent.
    """

    agent: str
    success: bool
    output: Any = None
    message: str = ""


@dataclass
class OrchestratorResult:
    """
    Complete result of processing one user query.
    """

    query: str
    route: QueryRoute

    agent_results: list[AgentExecutionResult] = field(
        default_factory=list
    )


class OrchestratorRuntime:
    """
    Main coordination layer for CACM-PHSS.

    Flow:

        Natural-language query
                |
                v
            QueryRouter
                |
                v
        Selected specialized agents
                |
                v
        Learning / Research / Coding
                |
                v
        Personalized student output

    IMPORTANT:

    This runtime does NOT invent assessment scores.

    Cognitive evidence should only enter CACM after the
    student actually answers a question, completes an
    assessment, or submits code.

    Simply viewing a lesson, paper, resource, or coding
    task is NOT treated as evidence of understanding.
    """

    def __init__(
        self,
        cognitive_engine: CognitiveEngine | None = None,
        query_router: QueryRouter | None = None,
    ):

        self.cognitive_engine = (
            cognitive_engine
            if cognitive_engine is not None
            else CognitiveEngine()
        )

        self.query_router = (
            query_router
            if query_router is not None
            else QueryRouter()
        )

        # ==================================================
        # LEARNING AGENT
        # ==================================================

        # Gemini is responsible only for generating
        # student-facing educational content.
        #
        # Gemini does NOT decide:
        #
        # - mastery
        # - confidence
        # - pedagogical action
        # - conflict state
        # - resource target difficulty
        #
        # Those decisions remain controlled by the
        # Learning Agent and CACM architecture.

        learning_content_provider = (
            GeminiContentProvider()
        )

        self.learning_runtime = (
            LearningAgentRuntime(
                cognitive_engine=self.cognitive_engine,
                content_provider=learning_content_provider,
            )
        )

        # ==================================================
        # RESEARCH AGENT
        # ==================================================

        self.paper_search = (
            AcademicPaperSearch()
        )

        self.semantic_ranker = (
            SemanticPaperRanker()
        )

        self.evidence_extractor = (
            ResearchEvidenceExtractor()
        )

        self.research_synthesizer = (
            ResearchSynthesizer()
        )

        # ==================================================
        # CODING AGENT
        # ==================================================

        self.coding_task_generator = (
            CodingTaskGenerator()
        )

    # ==================================================
    # MAIN ENTRY POINT
    # ==================================================

    def handle_query(
        self,
        student: StudentCognitiveModel,
        query: str,
    ) -> OrchestratorResult:
        """
        Route and execute a student's natural-language
        request.
        """

        if not isinstance(
            student,
            StudentCognitiveModel,
        ):
            raise TypeError(
                "student must be a StudentCognitiveModel."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        # ----------------------------------------------
        # STEP 1
        # UNDERSTAND THE STUDENT REQUEST
        # ----------------------------------------------

        route = self.query_router.route(
            query
        )

        results = []

        # ----------------------------------------------
        # STEP 2
        # EXECUTE ONLY THE SELECTED AGENTS
        # ----------------------------------------------

        for agent in route.selected_agents:

            if agent == "learning":

                result = self._run_learning(
                    student=student,
                    concept_name=route.concept,
                )

            elif agent == "research":

                result = self._run_research(
                    topic=route.concept,
                    question=query,
                )

            elif agent == "coding":

                result = self._run_coding(
                    student=student,
                    concept_name=route.concept,
                )

            else:

                result = AgentExecutionResult(
                    agent=agent,
                    success=False,
                    message=(
                        "Unsupported agent selected."
                    ),
                )

            results.append(
                result
            )

        return OrchestratorResult(
            query=query,
            route=route,
            agent_results=results,
        )

    # ==================================================
    # LEARNING EXECUTION
    # ==================================================

    def _run_learning(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> AgentExecutionResult:
        """
        Execute the complete Learning Agent experience.

        Flow:

            Observe CACM state
                    |
                    v
            Choose pedagogical action
                    |
                    v
            Build personalized content request
                    |
                    v
            Gemini generates student-facing lesson
                    |
                    v
            CACM-aware resource retrieval
                    |
                    v
            Difficulty estimation + ranking
                    |
                    v
            Return complete LearningExperience

        No cognitive evidence is created here.

        Reading a lesson or viewing a recommended
        resource is not evidence that the student
        understood the concept.
        """

        try:

            # ------------------------------------------
            # COMPLETE LEARNING EXPERIENCE
            # ------------------------------------------
            #
            # This now returns:
            #
            # LearningExperience
            #     activity
            #         personalized Gemini content
            #
            #     recommendations
            #         CACM-aware real resources
            # ------------------------------------------

            experience = (
                self.learning_runtime
                .get_learning_experience(
                    student=student,
                    concept_name=concept_name,
                    include_resources=True,
                    top_k=3,
                )
            )

            return AgentExecutionResult(
                agent="learning",
                success=True,
                output=experience,
                message=(
                    "Personalized learning experience "
                    "generated successfully."
                ),
            )

        except Exception as exc:

            return AgentExecutionResult(
                agent="learning",
                success=False,
                message=str(exc),
            )

    # ==================================================
    # RESEARCH EXECUTION
    # ==================================================

    def _run_research(
        self,
        topic: str,
        question: str,
    ) -> AgentExecutionResult:
        """
        Execute the grounded Research Agent pipeline.

        Search
            |
            v
        Semantic ranking
            |
            v
        Evidence extraction
            |
            v
        Grounded synthesis
        """

        try:

            # ------------------------------------------
            # STEP 1
            # SEARCH REAL ACADEMIC PAPERS
            # ------------------------------------------

            search_result = (
                self.paper_search.search(
                    query=question,
                    limit=5,
                )
            )

            papers = search_result.papers

            if not papers:

                return AgentExecutionResult(
                    agent="research",
                    success=False,
                    message=(
                        "No academic papers were found "
                        "for this query."
                    ),
                )

            # ------------------------------------------
            # STEP 2
            # SEMANTIC RANKING
            # ------------------------------------------

            ranked_papers = (
                self.semantic_ranker.rank(
                    query=question,
                    papers=papers,
                    candidate_limit=5,
                )
            )

            if not ranked_papers:

                return AgentExecutionResult(
                    agent="research",
                    success=False,
                    message=(
                        "Papers were retrieved, but no "
                        "relevant papers were ranked."
                    ),
                )

            # ------------------------------------------
            # STEP 3
            # EXTRACT GROUNDED EVIDENCE
            # ------------------------------------------

            evidence = (
                self.evidence_extractor
                .extract_from_ranked_papers(
                    question=question,
                    ranked_papers=ranked_papers,
                    max_claims_per_paper=2,
                )
            )

            if not evidence:

                return AgentExecutionResult(
                    agent="research",
                    success=False,
                    message=(
                        "Relevant papers were found, "
                        "but grounded evidence could "
                        "not be extracted."
                    ),
                )

            # ------------------------------------------
            # STEP 4
            # PRESERVE RANKED PAPER ORDER
            # ------------------------------------------

            papers_used = [
                ranked.paper
                for ranked in ranked_papers
            ]

            # ------------------------------------------
            # STEP 5
            # GROUNDED SYNTHESIS
            # ------------------------------------------

            synthesis = (
                self.research_synthesizer.synthesize(
                    topic=topic,
                    question=question,
                    evidence=evidence,
                    papers=papers_used,
                )
            )

            return AgentExecutionResult(
                agent="research",
                success=True,
                output=synthesis,
                message=(
                    "Research papers were retrieved, "
                    "ranked, and synthesized."
                ),
            )

        except Exception as exc:

            return AgentExecutionResult(
                agent="research",
                success=False,
                message=str(exc),
            )

    # ==================================================
    # CODING EXECUTION
    # ==================================================

    def _run_coding(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
    ) -> AgentExecutionResult:
        """
        Generate a coding task based on the student's
        shared cognitive state.
        """

        try:

            state = student.get_concept(
                concept_name
            )

            difficulty = (
                self._difficulty_from_state(
                    mastery=state.mastery,
                    confidence=state.confidence,
                )
            )

            task = (
                self.coding_task_generator.generate(
                    concept_name=concept_name,
                    difficulty=difficulty,
                )
            )

            return AgentExecutionResult(
                agent="coding",
                success=True,
                output=task,
                message=(
                    "Personalized coding task "
                    "generated successfully."
                ),
            )

        except Exception as exc:

            return AgentExecutionResult(
                agent="coding",
                success=False,
                message=str(exc),
            )

    # ==================================================
    # CURRENT CODING DIFFICULTY POLICY
    # ==================================================

    @staticmethod
    def _difficulty_from_state(
        mastery: float,
        confidence: float,
    ) -> str:
        """
        Convert shared cognitive state into coding-task
        difficulty.

        These thresholds are current project heuristics
        and should later be evaluated/calibrated.
        """

        if mastery < 0.40:
            return "easy"

        if mastery < 0.70:
            return "medium"

        if confidence < 0.50:
            return "hard"

        return "hard"