"""LangGraph workflow orchestration."""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import ResearchState
from app.agents.nodes import (
    intent_classifier_node,
    planner_node,
    researcher_node,
    writer_node,
    simple_chat_node,
    review_node
)
from app.core.config import settings


def create_research_workflow():
    """Build and compile the research agent workflow graph."""
    workflow = StateGraph(ResearchState)

    workflow.add_node("intent_classifier", intent_classifier_node)
    workflow.add_node("simple_chat", simple_chat_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("review", review_node)

    def route_after_intent(state: ResearchState) -> str:
        """Route based on intent classification."""
        current_step = state.get("current_step")
        if current_step == "chat":
            return "simple_chat"
        elif current_step == "completed":
            return "end"
        return "planner"

    def route_after_review(state: ResearchState) -> str:
        """Human-in-the-loop routing."""
        approved = state.get("approved", False)
        revision_count = state.get("revision_count", 0)

        if approved or revision_count >= 3:
            return "end"
        return "writer"

    workflow.set_entry_point("intent_classifier")

    workflow.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "simple_chat": "simple_chat",
            "planner": "planner",
            "end": END
        }
    )

    workflow.add_edge("simple_chat", END)

    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", "review")

    workflow.add_conditional_edges(
        "review",
        route_after_review,
        {
            "writer": "writer",
            "end": END
        }
    )

    compile_kwargs = {"checkpointer": MemorySaver()}
    if settings.ENABLE_HUMAN_REVIEW:
        compile_kwargs["interrupt_before"] = ["review"]

    return workflow.compile(**compile_kwargs)


research_graph = create_research_workflow()