"""
Orchestrator Agent: crude but honest intent routing for the zeroth-review demo.

For 4 days, keyword routing is the right call — it's simple, explainable to
reviewers, and easy to extend. Swap in an LLM-based router (few-shot intent
classification) in Phase 2 once the Education/Coding agents exist and routing
actually gets ambiguous.
"""
from backend.agents import research_agent
from backend.models import OrchestratorResponse

EDUCATION_KEYWORDS = {"learn", "course", "roadmap", "tutorial", "study plan"}
CODING_KEYWORDS = {"debug", "code review", "error", "stack trace", "fix my code"}


def _classify(query: str) -> str:
    q = query.lower()
    if any(kw in q for kw in EDUCATION_KEYWORDS):
        return "education_agent"  # not implemented yet — Phase 2
    if any(kw in q for kw in CODING_KEYWORDS):
        return "coding_agent"  # not implemented yet — Phase 2
    return "research_agent"


async def route(query: str,num_papers: int=3) -> OrchestratorResponse:
    target = _classify(query)

    if target == "research_agent":
        result = await research_agent.run(query,max_papers=num_papers)
        return OrchestratorResponse(routed_to=target, result=result.model_dump())

    # Stub responses for agents that are future scope — keeps the orchestrator
    # demoable end-to-end without pretending unbuilt agents work.
    return OrchestratorResponse(
        routed_to=target,
        result={
            "message": f"{target} is planned for Phase 2 and not yet implemented. "
            "Try a research/literature query instead."
        },
    )
