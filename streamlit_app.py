"""
PHSS Research Assistant — Streamlit UI
Run with: streamlit run streamlit_app.py
"""
import asyncio
import json
import sys
import os
from pathlib import Path

import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PHSS Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    color: white;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] p { color: white !important; }

/* Main background */
.main { background-color: #f8fafc; }

/* Hero banner */
.hero {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 50%, #7c3aed 100%);
    padding: 2.5rem 2rem; border-radius: 16px; color: white; margin-bottom: 1.5rem;
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0; }
.hero p  { font-size: 1rem; opacity: 0.85; margin: 0.4rem 0 0; }

/* Agent step pills */
.step-pill {
    display: inline-block; padding: 0.2rem 0.75rem; border-radius: 999px;
    font-size: 0.75rem; font-weight: 600; margin: 0.2rem;
}
.step-active  { background: #dbeafe; color: #1e40af; }
.step-done    { background: #dcfce7; color: #166534; }
.step-pending { background: #f1f5f9; color: #64748b; }

/* Cards */
.card {
    background: white; border-radius: 12px; padding: 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 1rem;
}
.card h3 { margin-top: 0; color: #1e3a5f; }

/* Gap badge */
.gap-high   { background: #fee2e2; color: #991b1b; border-radius: 6px; padding: 0.1rem 0.5rem; font-size: 0.75rem; }
.gap-medium { background: #fef3c7; color: #92400e; border-radius: 6px; padding: 0.1rem 0.5rem; font-size: 0.75rem; }
.gap-low    { background: #dcfce7; color: #166534; border-radius: 6px; padding: 0.1rem 0.5rem; font-size: 0.75rem; }

/* Q&A bubbles */
.qa-user      { background: #eff6ff; border-left: 4px solid #2563eb; padding: 0.8rem 1rem; border-radius: 8px; margin: 0.5rem 0; }
.qa-assistant { background: #f0fdf4; border-left: 4px solid #16a34a; padding: 0.8rem 1rem; border-radius: 8px; margin: 0.5rem 0; }
.qa-source    { font-size: 0.75rem; color: #64748b; margin-top: 0.4rem; }

/* Download buttons */
.stDownloadButton button {
    border-radius: 8px; font-weight: 600;
    background: linear-gradient(135deg, #1e3a5f, #2563eb);
    color: white; border: none;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def run_async(coro):
    """Run an async coroutine from Streamlit's sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def load_graph():
    """Lazy-load the LangGraph pipeline (cached across reruns)."""
    if "graph_loaded" not in st.session_state:
        with st.spinner("🔧 Loading research pipeline…"):
            try:
                from app.core.graph import research_graph
                st.session_state.research_graph = research_graph
                st.session_state.graph_loaded = True
            except Exception as e:
                st.error(f"Failed to load pipeline: {e}")
                st.session_state.graph_loaded = False
    return st.session_state.get("research_graph")


def build_initial_state(query: str) -> dict:
    return {
        "user_query": query, "topic": "", "intent": "",
        "pipeline": [], "papers": [], "extractions": [],
        "literature_review": None, "gap_analysis": None,
        "novelty_report": None, "report": None, "citations": None,
        "qa_request": None, "qa_response": None,
        "errors": [], "current_step": "manager_node", "retry_count": 0,
    }


PIPELINE_LABELS = {
    "search_node":     "🔍 Search Agent",
    "reading_node":    "📖 Reading Agent",
    "lit_review_node": "📝 Literature Review Agent",
    "gap_node":        "🔬 Gap Detection Agent",
    "novelty_node":    "💡 Novelty Agent",
    "writing_node":    "✍️ Writing Agent",
    "citation_node":   "📚 Citation Agent",
    "qa_node":         "💬 Q&A Agent",
}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 PHSS Research Assistant")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🏠 Home", "🔍 Research", "📄 Report Viewer", "💬 Q&A Chat"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### Pipeline Status")
    if "last_pipeline" in st.session_state:
        for node in st.session_state.last_pipeline:
            label = PIPELINE_LABELS.get(node, node)
            css   = "step-done" if node in st.session_state.get("completed_steps", []) else "step-pending"
            st.markdown(f'<span class="step-pill {css}">{label}</span>', unsafe_allow_html=True)
    else:
        st.caption("Run a research query to see the pipeline.")

    st.markdown("---")
    st.caption("Powered by LangGraph · ChromaDB · GPT-4o")


# ══════════════════════════════════════════════════════════════════════════════
# HOME PAGE
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.markdown("""
    <div class="hero">
        <h1>🔬 PHSS Research Assistant</h1>
        <p>AI-powered multi-agent literature research · From topic to full report in minutes</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    for col, icon, label, desc in [
        (col1, "🔍", "Search",   "Discovers papers from Semantic Scholar, arXiv & OpenAlex"),
        (col2, "📖", "Read",     "Parses PDFs and extracts structured knowledge"),
        (col3, "🔬", "Analyse",  "Identifies research gaps with evidence"),
        (col4, "📄", "Report",   "Generates a full report in PDF, DOCX & Markdown"),
    ]:
        with col:
            st.markdown(f"""
            <div class="card" style="text-align:center">
                <div style="font-size:2rem">{icon}</div>
                <h3 style="margin:0.3rem 0">{label}</h3>
                <p style="font-size:0.82rem;color:#64748b;margin:0">{desc}</p>
            </div>""", unsafe_allow_html=True)

    st.markdown("### 💬 Example queries you can try")
    examples = [
        "Generate a research report on Transformer models in NLP",
        "Find papers on federated learning in healthcare",
        "What are the research gaps in Vision Transformers?",
        "Suggest future research ideas for Graph Neural Networks in drug discovery",
        "Write a literature review on BERT and its variants",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state.prefill_query = ex
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# RESEARCH PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Research":
    st.markdown("""
    <div class="hero">
        <h1>🔍 Run Research Pipeline</h1>
        <p>Enter a research topic — the agents will find papers, extract knowledge, and generate a report.</p>
    </div>
    """, unsafe_allow_html=True)

    # Restore query from session or prefill from home page examples
    prefill = st.session_state.pop("prefill_query", "")
    default_query = prefill or st.session_state.get("last_query", "")
    query = st.text_area(
        "Research Query",
        value=default_query,
        placeholder="e.g. Generate a research report on federated learning in healthcare",
        height=100,
    )

    col_a, col_b, col_c = st.columns([1, 1, 3])
    with col_a:
        run_btn = st.button("🚀 Run Pipeline", type="primary", use_container_width=True)
    with col_b:
        clear_btn = st.button("🗑️ Clear Results", use_container_width=True)
    with col_c:
        st.caption("This may take 1–3 minutes depending on the number of papers found.")

    if clear_btn:
        for key in ["final_state", "last_query", "last_pipeline", "completed_steps"]:
            st.session_state.pop(key, None)
        st.rerun()

    if run_btn and query.strip():
        # Save query so it survives page navigation
        st.session_state.last_query = query

        graph = load_graph()
        if not graph:
            st.stop()

        st.markdown("### 🔄 Pipeline Running…")
        progress_bar = st.progress(0, text="Starting…")

        with st.spinner("Pipeline executing…"):
            try:
                state = build_initial_state(query)
                final = run_async(graph.ainvoke(state))

                st.session_state.final_state     = final
                st.session_state.last_pipeline   = final.get("pipeline", [])
                st.session_state.completed_steps = final.get("pipeline", [])
                progress_bar.progress(100, text="✅ Complete!")

            except Exception as e:
                st.error(f"Pipeline error: {e}")
                st.stop()

    # ── Results — shown whenever final_state exists (persists across navigation) ──
    if "final_state" in st.session_state:
        final  = st.session_state.final_state
        report = final.get("report") or {}
        papers = final.get("papers", [])
        errors = final.get("errors", [])

        # ── Summary metrics ──
        st.markdown("### ✅ Pipeline Complete")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Papers Found",    len(papers))
        m2.metric("Papers Read",     len(final.get("extractions", [])))
        gaps = (final.get("gap_analysis") or {}).get("gaps", [])
        m3.metric("Gaps Identified", len(gaps))
        m4.metric("Intent Detected", final.get("intent", "—").replace("_", " ").title())

        if errors:
            with st.expander(f"⚠️ {len(errors)} warnings during pipeline"):
                for e in errors:
                    st.warning(e)

        # ── Papers table ──
        if papers:
            with st.expander(f"📚 {len(papers)} Papers Discovered", expanded=False):
                for p in papers:
                    cols = st.columns([3, 1, 1, 1])
                    cols[0].markdown(f"**{p.get('title','—')}**")
                    cols[1].caption(", ".join(p.get("authors", [])[:2]))
                    cols[2].caption(str(p.get("year", "—")))
                    cols[3].caption(p.get("source", "—"))

        # ── Downloads ──
        if report.get("markdown_path"):
            st.markdown("### 📥 Download Report")
            dl1, dl2, dl3 = st.columns(3)
            for col, fmt, path_key, mime in [
                (dl1, "📄 Markdown", "markdown_path", "text/markdown"),
                (dl2, "📝 DOCX",     "docx_path",     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                (dl3, "🖨️ PDF",      "pdf_path",      "application/pdf"),
            ]:
                fpath = report.get(path_key)
                if fpath and Path(fpath).exists():
                    with col:
                        st.download_button(
                            label=fmt,
                            data=Path(fpath).read_bytes(),
                            file_name=Path(fpath).name,
                            mime=mime,
                            use_container_width=True,
                        )

        if report:
            st.info("👆 Go to **📄 Report Viewer** to read the full report, or **💬 Q&A Chat** to ask questions about it.")


# ══════════════════════════════════════════════════════════════════════════════
# REPORT VIEWER
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📄 Report Viewer":
    st.markdown("""
    <div class="hero">
        <h1>📄 Report Viewer</h1>
        <p>Read the generated research report section by section.</p>
    </div>
    """, unsafe_allow_html=True)

    if "final_state" not in st.session_state:
        st.info("No report yet. Go to **🔍 Research** and run a query first.")
        st.stop()

    final  = st.session_state.final_state
    report = final.get("report") or {}

    if not report:
        st.warning("The pipeline completed but no report was generated.")
        st.stop()

    st.markdown(f"# {report.get('title', 'Research Report')}")
    st.caption(f"Topic: **{report.get('topic', '—')}** · Generated: {report.get('generated_at', '—')[:10]}")
    st.markdown("---")

    sections = [
        ("📋 Abstract",              report.get("abstract", "")),
        ("1️⃣ Introduction",         report.get("introduction", "")),
        ("2️⃣ Literature Review",    report.get("literature_review", "")),
        ("3️⃣ Comparative Analysis", report.get("comparative_analysis", "")),
        ("4️⃣ Research Gaps",        report.get("research_gaps", "")),
        ("5️⃣ Future Directions",    report.get("future_directions", "")),
    ]

    tab_labels = [s[0] for s in sections]
    tabs = st.tabs(tab_labels)
    for tab, (_, content) in zip(tabs, sections):
        with tab:
            st.markdown(content or "_Section not available._")

    # ── Research Gaps visual breakdown ──
    gap_analysis = final.get("gap_analysis") or {}
    gaps = gap_analysis.get("gaps", [])
    if gaps:
        st.markdown("---")
        st.markdown("### 🔬 Research Gaps Summary")
        for g in gaps:
            sev   = g.get("severity", "medium")
            badge = f'<span class="gap-{sev}">{sev.upper()}</span>'
            st.markdown(
                f'<div class="card"><b>{g.get("gap_type","").replace("_"," ").title()}</b> &nbsp; {badge}<br>'
                f'{g.get("description","")}<br><span style="font-size:0.75rem;color:#64748b">Evidence: {", ".join(g.get("evidence",[]))}</span></div>',
                unsafe_allow_html=True,
            )

    # ── References ──
    citations = report.get("citations") or {}
    ieee = citations.get("ieee", [])
    if ieee:
        with st.expander("📚 References (IEEE)"):
            for i, ref in enumerate(ieee, 1):
                st.markdown(f"[{i}] {ref}")

    # ── Downloads ──
    st.markdown("---")
    st.markdown("### 📥 Download")
    dl1, dl2, dl3 = st.columns(3)
    for col, fmt, path_key, mime in [
        (dl1, "📄 Markdown", "markdown_path", "text/markdown"),
        (dl2, "📝 DOCX",     "docx_path",     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (dl3, "🖨️ PDF",      "pdf_path",      "application/pdf"),
    ]:
        fpath = report.get(path_key)
        if fpath and Path(fpath).exists():
            with col:
                st.download_button(
                    label=fmt,
                    data=Path(fpath).read_bytes(),
                    file_name=Path(fpath).name,
                    mime=mime,
                    use_container_width=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# Q&A CHAT PAGE
# ══════════════════════════════════════════════════════════════════════════════
elif page == "💬 Q&A Chat":
    st.markdown("""
    <div class="hero">
        <h1>💬 Research Q&A</h1>
        <p>Ask any question about the generated report or the analyzed papers. Answers are grounded in retrieved context only.</p>
    </div>
    """, unsafe_allow_html=True)

    if "final_state" not in st.session_state:
        st.info("No report yet. Go to **🔍 Research** and run a query first.")
        st.stop()

    report = (st.session_state.final_state.get("report") or {})
    report_id = report.get("report_id", "session_default")

    if "qa_history" not in st.session_state:
        st.session_state.qa_history = []

    # ── Mode selector ──
    mode = st.selectbox(
        "Question mode",
        ["general", "explain_paper", "compare_papers", "summarize_section", "explain_term"],
        format_func=lambda x: {
            "general":          "💬 General question",
            "explain_paper":    "🎓 Explain a paper simply",
            "compare_papers":   "⚖️ Compare papers",
            "summarize_section":"📋 Summarize a section",
            "explain_term":     "📖 Explain a term / concept",
        }[x],
    )

    # ── Quick-fire example questions ──
    with st.expander("💡 Example questions to try"):
        example_qs = [
            "What datasets are most commonly used across the papers?",
            "Which paper achieves the best results and why?",
            "What are the main limitations identified?",
            "Compare the methodologies used in the papers.",
            "Explain the key concept in simple terms.",
        ]
        for q in example_qs:
            if st.button(q, key=f"qa_ex_{q[:20]}"):
                st.session_state.qa_prefill = q
                st.rerun()

    # ── Chat history display ──
    for turn in st.session_state.qa_history:
        st.markdown(f'<div class="qa-user">🧑 <b>You:</b> {turn["question"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="qa-assistant">🤖 <b>Assistant:</b><br>{turn["answer"]}</div>', unsafe_allow_html=True)
        if turn.get("sources"):
            src_text = " · ".join(
                f'{s["paper_id"]} ({round(s["relevance_score"]*100)}%)'
                for s in turn["sources"][:4]
            )
            st.markdown(f'<div class="qa-source">📄 Sources: {src_text}</div>', unsafe_allow_html=True)
        st.markdown("")

    # ── Input ──
    prefill_q = st.session_state.pop("qa_prefill", "")
    question  = st.chat_input("Ask a question about the report or papers…") or prefill_q

    if question:
        graph = load_graph()
        if not graph:
            st.stop()

        with st.spinner("🔍 Searching knowledge base…"):
            try:
                state = {
                    "user_query": question, "topic": "", "intent": "qa",
                    "pipeline": ["qa_node"], "papers": [], "extractions": [],
                    "literature_review": None, "gap_analysis": None, "novelty_report": None,
                    "report": {"report_id": report_id}, "citations": None,
                    "qa_request": {"report_id": report_id, "question": question, "mode": mode},
                    "qa_response": None, "errors": [], "current_step": "qa_node", "retry_count": 0,
                }
                final = run_async(graph.ainvoke(state))
                qa_resp = final.get("qa_response") or {}

                if qa_resp:
                    st.session_state.qa_history.append({
                        "question": question,
                        "answer":   qa_resp.get("answer", "No answer returned."),
                        "sources":  qa_resp.get("sources", []),
                        "grounded": qa_resp.get("grounded", False),
                    })
                    st.rerun()
                else:
                    st.error("No response from Q&A agent.")
            except Exception as e:
                st.error(f"Q&A error: {e}")

    if st.session_state.qa_history:
        if st.button("🗑️ Clear chat history"):
            st.session_state.qa_history = []
            st.rerun()
