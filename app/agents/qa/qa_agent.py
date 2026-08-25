from __future__ import annotations
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.knowledge_base.chroma_client import KnowledgeBase
from app.models.qa import QARequest, QAResponse, RetrievedChunk

logger = logging.getLogger(__name__)
_kb = KnowledgeBase()

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a research Q&A assistant.
Answer ONLY from the retrieved context below.
If the context is insufficient, say exactly:
"I don't have enough information in the retrieved papers to answer this."

Always cite the source paper(s) you reference.
Never hallucinate facts, numbers, or paper titles.

Retrieved Context:
{context}

Question: {question}
Mode: {mode}

Mode instructions:
- explain_paper: Explain this paper's contribution simply, as if to a student.
- compare_papers: Create a structured comparison.
- summarize_section: Provide a concise structured summary.
- explain_term: Define the term, then explain how it is used in these papers.
- general: Answer directly and cite your sources.

Provide a well-structured answer. List the paper(s) you referenced at the end."""),
])


async def qa_node(state: AgentState) -> dict:
    qa_req = state.get("qa_request")
    if not qa_req:
        return {"qa_response": None}

    req = QARequest(**qa_req) if isinstance(qa_req, dict) else qa_req
    report    = state.get("report") or {}
    report_id = report.get("report_id", "session_default")

    chunks = _kb.retrieve_chunks(
        query=req.question,
        report_id=report_id,
        n_results=8,
        paper_ids=req.paper_ids,
    )

    if not chunks:
        return {
            "qa_response": QAResponse(
                question=req.question,
                answer="I don't have enough information in the retrieved papers to answer this.",
                sources=[],
                confidence=0.0,
                grounded=False,
            ).model_dump()
        }

    context = "\n---\n".join(
        f"[{c['metadata']['paper_id']}] {c['metadata']['title']}\n{c['text']}"
        for c in chunks
    )

    llm   = get_llm(temperature=0.1)
    chain = _PROMPT | llm
    result = await chain.ainvoke({
        "context":  context[:7000],
        "question": req.question,
        "mode":     req.mode,
    })

    sources = [
        RetrievedChunk(
            text=c["text"],
            paper_id=c["metadata"]["paper_id"],
            paper_title=c["metadata"]["title"],
            relevance_score=c["score"],
        )
        for c in chunks
    ]
    avg_score = sum(c["score"] for c in chunks) / len(chunks)

    return {
        "qa_response": QAResponse(
            question=req.question,
            answer=result.content,
            sources=sources,
            confidence=round(avg_score, 3),
            grounded=True,
        ).model_dump()
    }
