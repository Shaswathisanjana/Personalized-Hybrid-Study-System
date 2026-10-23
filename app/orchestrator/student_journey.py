"""Application services connecting existing workflows through one shared CACM."""
from copy import deepcopy

from app.cognitive.concept_identity import clean_concept_name, concept_id
from app.coding_agent.agent import CodingAgent
from app.coding_agent.verified_exercises import VERIFIED_CONCEPTS
from app.learning_agent.agent import LearningAgent
from app.learning_agent.study_planner import LearningStudyPlanner
from app.research_agent.intelligent_planner import IntelligentResearchPlanner


PAGES = {"learning": "Student View", "coding": "Advanced Coding Agent", "research": "Advanced Research Agent"}


class StudentJourneyService:
    def __init__(self, student, orchestrator):
        self.student, self.orchestrator = student, orchestrator
        self.engine = orchestrator.cognitive_engine

    @staticmethod
    def coding_concept(name):
        return next((topic for topic in VERIFIED_CONCEPTS if concept_id(topic) == concept_id(name)), None)

    def observe(self, concept):
        """Read shared evidence and preview actual policies without creating priors."""
        concept = clean_concept_name(concept)
        state = self.student.find_concept(concept)
        conflict = bool(LearningStudyPlanner.has_conflict(self.student, self.engine, concept))
        # Existing decision policies can create a neutral concept. Preview on a
        # detached student so displaying the common panel remains read-only.
        preview = deepcopy(self.student)
        evidence = self.engine.evidence_store.get_evidence_for_concept(self.student.user_id, concept)
        sources = {}
        for item in evidence:
            sources[item.source_agent] = sources.get(item.source_agent, 0) + 1
        return dict(concept=concept, identity=concept_id(concept), has_conflict=conflict,
                    mastery=state.mastery if state else None,
                    confidence=state.confidence if state else None, attempts=state.attempts if state else 0,
                    evidence_sources=sources, coding_available=self.coding_concept(concept) is not None,
                    learning=LearningAgent().choose_action(preview, concept, conflict),
                    coding=CodingAgent().choose_action(preview, concept, conflict),
                    research=IntelligentResearchPlanner().create_plan(preview, concept, concept, conflict).action)

    def handoff(self, agent, concept, *, query="", diagnostic=False):
        concept = clean_concept_name(concept)
        if agent not in PAGES:
            raise ValueError("Unsupported study workflow.")
        if agent == "coding" and self.coding_concept(concept) is None:
            raise ValueError("Verified coding practice is not available for this exact topic.")
        if diagnostic and not self.observe(concept)["has_conflict"]:
            raise ValueError("Diagnostic navigation requires a genuine unresolved conflict.")
        return dict(kind="study_workflow", user_id=self.student.user_id, agent=agent,
                    concept=concept, query=query.strip(), diagnostic=bool(diagnostic))

    def handle_request(self, query, *, defer_workflows=False):
        """Keep learning execution; hand other intents to the richer saved workflows.

        Legacy embedded orchestrators without a router retain their existing
        public entry point. The production orchestrator always has a router.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Enter a study request.")
        if not hasattr(self.orchestrator, "query_router"):
            return self.orchestrator.handle_query(self.student, query.strip())
        from app.orchestrator.orchestrator_runtime import OrchestratorResult, AgentExecutionResult
        route = self.orchestrator.query_router.route(query.strip())
        results = []
        for agent in route.selected_agents:
            if defer_workflows:
                if agent not in PAGES:
                    raise ValueError("Unsupported study workflow.")
                output = dict(kind="study_workflow", user_id=self.student.user_id, agent=agent,
                              concept=clean_concept_name(route.concept), query=query.strip())
                results.append(AgentExecutionResult(agent, True, output, "Activity ready to open."))
            elif agent == "learning":
                results.append(self.orchestrator._run_learning(self.student, route.concept))
            else:
                try:
                    output = self.handoff(agent, route.concept, query=query)
                    results.append(AgentExecutionResult(agent, True, output,
                        "Continue to the saved workflow to generate content and assess your own work."))
                except ValueError as exc:
                    results.append(AgentExecutionResult(agent, False, message=str(exc)))
        return OrchestratorResult(query.strip(), route, results)

    def coding_workflow(self):
        from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
        return IntegratedCodingWorkflow(self.student, self.engine)

    def research_coordinator(self, coordinator_factory=None, **kwargs):
        from app.research_agent.personalized_coordinator import PersonalizedResearchCoordinator
        factory = coordinator_factory or PersonalizedResearchCoordinator
        return factory(self.student, self.engine, **kwargs)


def request_navigation(state, agent, concept, *, query="", diagnostic=False):
    service = StudentJourneyService(state["student"], state["orchestrator"])
    state["journey_navigation"] = service.handoff(agent, concept, query=query, diagnostic=diagnostic)


def apply_navigation(state):
    """Consume an owner-scoped handoff before Streamlit instantiates widgets."""
    pending = state.get("journey_navigation")
    if pending is None:
        return
    if pending.get("user_id") != state["student"].user_id:
        raise ValueError("This navigation request belongs to another student.")
    service = StudentJourneyService(state["student"], state["orchestrator"])
    # Revalidate topic support at consumption; completed diagnostics may already
    # have removed the conflict, so navigation never manufactures one.
    valid = service.handoff(pending["agent"], pending["concept"], query=pending.get("query", ""))
    agent, concept = valid["agent"], valid["concept"]
    state["journey_topic"] = concept
    state["journey_topic_draft"] = concept
    state["_app_page"] = PAGES[agent]
    if agent == "coding":
        state["advanced_coding_target_concept"] = service.coding_concept(concept)
    elif agent == "research":
        state["advanced_research_topic_input"] = concept
        state["advanced_research_concept_input"] = concept
        if pending.get("diagnostic") and state.get("research_diagnostic_session") is None:
            existing = state["student"].find_concept(concept)
            state["research_other_conflict"] = existing.concept_name if existing else concept
    else:
        state["learning_goal"] = concept
        state["learning_request_input"] = "Teach me " + concept
        state.pop("learning_plan_goal_choice", None)
        state.pop("learning_plan_custom_goal", None)
    state.pop("journey_navigation", None)
