from __future__ import annotations
from langgraph.graph import StateGraph, END
from app.core.state import AgentState
from app.core.router import route_from_manager, route_next

# Agent node imports
from app.agents.manager.manager_agent import manager_node, error_node
from app.agents.search.search_agent import search_node
from app.agents.reading.reading_agent import reading_node
from app.agents.analysis.analysis_node import analysis_node   # merged: lit-review + gap + novelty
from app.agents.writing.writing_agent import writing_node
from app.agents.citation.citation_agent import citation_node
from app.agents.qa.qa_agent import qa_node

PIPELINE_NODES = [
    "search_node", "reading_node", "analysis_node",
    "writing_node", "citation_node", "qa_node",
]


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("manager_node",  manager_node)
    graph.add_node("search_node",   search_node)
    graph.add_node("reading_node",  reading_node)
    graph.add_node("analysis_node", analysis_node)  # merged: lit-review + gap + novelty
    graph.add_node("writing_node",  writing_node)
    graph.add_node("citation_node", citation_node)
    graph.add_node("qa_node",       qa_node)
    graph.add_node("error_node",    error_node)

    graph.set_entry_point("manager_node")

    # Manager → first pipeline node
    graph.add_conditional_edges(
        "manager_node",
        route_from_manager,
        {n: n for n in PIPELINE_NODES} | {"error_node": "error_node"},
    )

    # Each pipeline node → next node or END
    for node in PIPELINE_NODES:
        graph.add_conditional_edges(
            node,
            route_next,
            {n: n for n in PIPELINE_NODES} | {"error_node": "error_node", END: END},
        )

    # Error recovery
    graph.add_conditional_edges(
        "error_node",
        lambda s: END if s.get("retry_count", 0) >= 3 else s.get("current_step", END),
        {n: n for n in PIPELINE_NODES} | {END: END},
    )

    return graph.compile()


research_graph = build_graph()
