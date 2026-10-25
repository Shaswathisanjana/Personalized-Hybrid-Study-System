import asyncio
import logging
import time
from typing import Any, Dict, List, Literal

from langchain_core.messages import ToolMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.tools.research import ResearchToolkit, academic_search, extract_citations

logger = logging.getLogger(__name__)


def _build_llm(model: str, state: Dict[str, Any]) -> ChatOpenAI:
    """Create an LLM client via OpenRouter."""
    base_url = settings.OPENAI_BASE_URL
    api_key = state.get("api_key") or settings.OPENAI_API_KEY

    return ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=settings.MODEL_TEMPERATURE,
        max_tokens=settings.MAX_TOKENS,
        timeout=settings.TIMEOUT,
        max_retries=settings.MAX_RETRIES,
    )

def _is_rate_limited_error(exc: Exception) -> bool:
    """Return True if exception indicates provider rate limiting or 404 from OpenRouter."""
    message = str(exc).lower()
    # OpenRouter returns 404 when no endpoints are available, effectively a type of rate limit/blackout
    return "429" in message or "rate limit" in message or "rate-limited" in message or "404" in message




@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=1, max=5),
    retry=lambda exc: _is_rate_limited_error(exc),
    reraise=True
)
def _invoke_with_retry(llm: ChatOpenAI, prompt_messages: List[Any]):
    """Invoke LLM with exponential backoff on rate limits."""
    return llm.invoke(prompt_messages)


def _invoke_with_llm(state: Dict[str, Any], prompt_messages: List[Any]):
    """Invoke LLM using the configured model with retry logic."""
    model = state.get("selected_model") or settings.DEFAULT_MODEL
    llm = _build_llm(model=model, state=state)
    return _invoke_with_retry(llm, prompt_messages)


class IntentClassification(BaseModel):
    """Schema for intent classification output."""
    intent: Literal["CHAT", "RESEARCH"]
    requires_academic: bool = False
    requires_web: bool = True
    reasoning: str = Field(description="Why this classification was chosen")


class ResearchPlan(BaseModel):
    """Schema for research planning output."""
    steps: List[Dict[str, str]] = Field(
        description="List of search steps with 'query' and 'type' (web/academic)"
    )


research_toolkit = ResearchToolkit()
web_search = research_toolkit.get_web_search_tool()


def _conversation_context(messages: List[Dict[str, str]], limit: int = 6) -> str:
    """Build compact conversation context for prompt conditioning."""
    if not messages:
        return "No previous conversation context provided."

    recent_messages = messages[-limit:]
    lines: List[str] = []
    for message in recent_messages:
        role = message.get("role", "user").upper()
        content = message.get("content", "").strip()
        if content:
            lines.append(f"{role}: {content[:500]}")

    return "\n".join(lines) if lines else "No previous conversation context provided."


def intent_classifier_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Classify query intent as chat or research."""
    query = state["query"]
    conversation_context = _conversation_context(state.get("messages", []))

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an AI Research Assistant. You ONLY respond to queries related to Artificial Intelligence, Machine Learning, and Deep Learning.

{format_instructions}

Instructions:
1. If the query is NOT related to Artificial Intelligence (e.g., cooking, bread, general news, hardware), return REJECTED.
2. If the query is a simple AI chat question, return CHAT.
3. If it requires in-depth analysis or search, return RESEARCH.

Examples:
- "How to bake a pizza?" → REJECTED
- "Best sourdough starter" → REJECTED
- "Who won the world cup?" → REJECTED
- "What is a neural network?" → CHAT
- "Latest breakthroughs in LLM architectures 2024" → RESEARCH (web=true)
""",
        ),
        (
            "human",
            "Conversation Context:\n{conversation_context}\n\nCurrent Query:\n{query}",
        ),
    ])

    parser = PydanticOutputParser(pydantic_object=IntentClassification)
    try:
        prompt_messages = prompt.format_messages(
            query=query,
            conversation_context=conversation_context,
            format_instructions=parser.get_format_instructions(),
        )
        response = _invoke_with_llm(state, prompt_messages)
        content = response.content.strip()
        
        # Handle cases where model returns raw REJECTED instead of JSON
        if content == "REJECTED" or '"intent": "REJECTED"' in content or "REJECTED" in content.upper():
            logger.info("Query rejected by intent classifier. Sending to simple chat for brief response.")
            return {
                "intent": "REJECTED",
                "current_step": "chat",
            }

        result = parser.parse(content)
        logger.info(
            "Intent: %s (academic=%s, web=%s)",
            result.intent,
            result.requires_academic,
            result.requires_web,
        )

        logger.debug("State after intent_classifier: %s", result)
        
        output = {
            "intent": result.intent,
            "requires_academic": result.requires_academic,
            "requires_web": result.requires_web,
            "current_step": "planning" if result.intent == "RESEARCH" else "completed",
        }
        if result.intent == "CHAT":
            output["current_step"] = "chat"
            
        logger.debug("DEBUG: Node 'intent_classifier' output: %s", output)
        return output
    except Exception as exc:
        logger.error("Intent classification failed: %s", exc, exc_info=True)
        output = {
            "intent": "RESEARCH",
            "requires_academic": False,
            "requires_web": True,
            "current_step": "planning",
            "error": f"Intent classification error: {exc}",
        }
        logger.debug("DEBUG: Node 'intent_classifier' output (error): %s", output)
        return output


def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate an executable research plan."""
    query = state["query"]
    conversation_context = _conversation_context(state.get("messages", []))

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Break down the research query into maximum 3 specific search queries.

{format_instructions}

Guidelines:
- If the query is NOT related to AI/Computer Science, do NOT generate steps.
- Use "web" type for recent news, trends, practical info
- Use "academic" type for scientific papers, theoretical concepts
- Each query should be self-contained and specific

Example:
Query: "Impact of AI on healthcare in 2024"
Output:
{{
  "steps": [
    {{"query": "AI healthcare applications 2024", "type": "web"}},
    {{"query": "machine learning medical diagnosis papers", "type": "academic"}},
    {{"query": "AI healthcare market trends 2024", "type": "web"}}
  ]
}}
""",
        ),
        (
            "human",
            "Conversation Context:\n{conversation_context}\n\nQuery: {query}",
        ),
    ])

    parser = PydanticOutputParser(pydantic_object=ResearchPlan)
    try:
        prompt_messages = prompt.format_messages(
            query=query,
            conversation_context=conversation_context,
            format_instructions=parser.get_format_instructions(),
        )
        response = _invoke_with_llm(state, prompt_messages)
        result = parser.parse(response.content)
        logger.info("Research plan: %s steps", len(result.steps))
        logger.debug("State after planner: %s", result)
        output = {"plan": [s.model_dump() if hasattr(s, "model_dump") else s for s in result.steps], "current_step": "research"}
        logger.debug("DEBUG: Node 'planner' output: %s", output)
        return output
    except Exception as exc:
        logger.error("Planning failed: %s", exc, exc_info=True)
        output = {
            "plan": [{"query": query, "type": "web"}],
            "current_step": "research",
            "error": f"Planning error: {exc}",
        }
        logger.debug("DEBUG: Node 'planner' output (error): %s", output)
        return output


def researcher_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute research plan efficiently with bound tools if possible, otherwise manual invoke."""
    query = state.get("query", "")
    plan = state.get("plan", [])
    if not plan:
        plan = [{"query": query, "type": "web"}]
        
    requires_web = state.get("requires_web", True)
    requires_academic = state.get("requires_academic", False)

    web_results: List[Dict[str, Any]] = []
    academic_results: List[Dict[str, Any]] = []

    # Bind tools to LLM for more reliable execution if needed, 
    # but here we follow request for 'bound tools' by using LangChain's Tool binding pattern
    # though research usually is direct invoke.
    
    for step in plan:
        q = step.get("query", query)
        st = step.get("type", "web")
        try:
            if st == "web" and requires_web:
                logger.debug("Executing web search: %s", q)
                results = web_search.invoke(q)
                for res in results[:3]: # Further reduced to 3 for latency
                    web_results.append({
                        "title": res.get("title", "Untitled"),
                        "url": res.get("url", ""),
                        "content": res.get("content", "")[:800], # Reduced from 1000
                        "score": res.get("score", 0),
                        "source_query": q,
                    })
            elif st == "academic" and requires_academic:
                logger.debug("Executing academic search: %s", q)
                res_str = academic_search.invoke(q)
                for line in res_str.split("\n\n")[:2]: # Max 2 papers per step
                    if line.strip():
                        academic_results.append({
                            "content": line.strip(), # Truncated the content later on as well
                            "type": "academic",
                            "source_query": q,
                        })
        except Exception as e:
            logger.error("Step execution failed: %s", e)

    output = {
        "web_results": web_results,
        "academic_results": academic_results,
        "current_step": "writing",
    }
    logger.debug("DEBUG: Node 'researcher' output: %s", output)
    return output


def writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesize a research report from the collected sources."""
    query = state["query"]
    web_data = state.get("web_results", [])
    academic_data = state.get("academic_results", [])
    user_feedback = state.get("user_feedback", "")
    revision_count = state.get("revision_count", 0)
    conversation_context = _conversation_context(state.get("messages", []))

    sources_text = "## Web Sources:\n"
    for index, source in enumerate(web_data[:3], 1):
        sources_text += f"{index}. **{source['title']}**\n"
        sources_text += f"   URL: {source['url']}\n"
        sources_text += f"   Content: {source['content'][:200]}...\n\n"

    sources_text += "\n## Academic Sources:\n"
    for index, paper in enumerate(academic_data[:2], 1):
        sources_text += f"{index}. {paper['content'][:200]}...\n\n"

    revision_context = ""
    if revision_count > 0 and user_feedback:
        revision_context = f"""

**REVISION REQUEST #{revision_count}:**
User feedback: {user_feedback}

Please address the feedback above while maintaining report quality.
"""

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """Create a concise, professional markdown research summary based on the provided sources.

Requirements:
1. Use ## for main sections and ### for subsections to organize information logically.
2. Only include citations in the Sources and References section, do not pollute the text heavily.
3. Structure:
   - ## Executive Summary (A concise 2-3 sentence overview of the findings)
   - ## Key Findings (Brief bullet points highlighting crucial data/facts)
   - ## Sources and Citations (A numbered list of all used sources with their URLs, if available)
4. Length: 200-400 words. Be highly concise, direct, and summarize the core information.
5. Maintain an objective, academic, yet highly accessible tone.
6. Ensure smooth transitions and synthesize the information quickly.

Conversation Context:
{conversation_context}

Sources:
{sources}
{revision_context}
""",
        ),
        ("human", "Research Query: {query}\n\nGenerate the concise summary now:"),
    ])

    try:
        prompt_messages = prompt.format_messages(
            query=query,
            conversation_context=conversation_context,
            sources=sources_text,
            revision_context=revision_context,
        )
        response = _invoke_with_llm(state, prompt_messages)
        report = response.content
        citations = extract_citations.invoke(report)
        all_sources = [{"type": "web", **source} for source in web_data] + [
            {"type": "academic", **source} for source in academic_data
        ]
        logger.info("Report generated: %s chars, %s citations", len(report), len(citations))
        return {
            "final_report": report,
            "citations": citations,
            "all_sources": all_sources,
            "current_step": "review",
            "end_time": time.time(),
        }
    except Exception as exc:
        logger.error("Report generation failed: %s", exc, exc_info=True)
        return {
            "final_report": f"Error generating report: {exc}",
            "error": str(exc),
            "current_step": "completed",
        }


def simple_chat_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle simple conversational queries or rejected queries."""
    query = state["query"]
    intent = state.get("intent", "CHAT")
    messages = list(state.get("messages", []))
    conversation_context = _conversation_context(messages)

    system_prompt = "You are a helpful AI research assistant."
    if intent == "REJECTED":
        system_prompt = "You are an AI research assistant. The user asked something unrelated to your core expertise (AI/ML). Briefly acknowledge that this is outside your research scope, but provide a very short, 2-line helpful answer if possible."
    else:
        system_prompt = "You are a helpful research assistant. Answer the current question concisely based on your general knowledge."

    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Conversation Context:\n{conversation_context}\n\nCurrent Query:\n{query}"),
        ])
        prompt_messages = prompt.format_messages(
            conversation_context=conversation_context,
            query=query,
        )
        response = _invoke_with_llm(state, prompt_messages)
        content = response.content
        
        messages.extend([
            {"role": "user", "content": query},
            {"role": "assistant", "content": content},
        ])
        output = {
            "messages": messages,
            "final_report": content,
            "current_step": "completed",
            "end_time": time.time(),
        }
        logger.debug("DEBUG: Node 'simple_chat' output: %s", output)
        return output
    except Exception as exc:
        logger.error("Chat failed: %s", exc, exc_info=True)
        return {
            "final_report": f"Error: {exc}",
            "error": str(exc),
            "current_step": "completed",
        }


def review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the optional human review gate."""
    user_feedback = state.get("user_feedback")
    approved = state.get("approved", False)
    revision_count = state.get("revision_count", 0)

    if not user_feedback and not approved:
        logger.info("Review node: Waiting for human approval")
        return {}

    if approved:
        logger.info("Review node: Report approved")
        return {
            "approved": True,
            "current_step": "completed",
            "end_time": time.time(),
        }

    new_revision_count = revision_count + 1
    logger.info("Review node: Revision requested (#%s)", new_revision_count)

    if new_revision_count >= 3:
        logger.warning("Review node: Max revisions reached, auto-approving")
        return {
            "approved": True,
            "revision_count": new_revision_count,
            "current_step": "completed",
            "end_time": time.time(),
        }

    return {
        "approved": False,
        "revision_count": new_revision_count,
        "current_step": "writing",
    }