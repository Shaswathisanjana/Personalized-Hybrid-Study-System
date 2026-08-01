"""
Streamlit frontend for the zeroth-review demo.
Run the backend first (uvicorn backend.main:app --reload), then:
    streamlit run frontend/app.py
"""
import os
import pandas as pd
import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Multi-Agent Research Platform", layout="wide")
st.title("🔬 Multi-Agent Research & Learning Platform")
st.caption("Zeroth-review MVP — Orchestrator + Research Agent (RAG) live. "
           "Education Agent & Coding Agent: Phase 2.")

tab_query, tab_dashboard = st.tabs(["Ask a research question", "Activity dashboard"])

with tab_query:
    query = st.text_input(
        "Enter a research topic",
        placeholder="e.g. retrieval augmented generation for code review",
    )
    max_papers = st.slider("Number of papers to fetch", 3, 10, 6)

    if st.button("Run", type="primary") and query:
        with st.spinner("Orchestrator routing query → agent fetching & summarizing papers…"):
            resp = requests.post(
                f"{BACKEND_URL}/query", json={"query": query}, timeout=120
            )
        if resp.status_code != 200:
            st.error(f"Backend error: {resp.text}")
        else:
            data = resp.json()
            st.info(f"Routed to: **{data['routed_to']}**")
            result = data["result"]

            if "papers" in result and result["papers"]:
                st.subheader("Comparison table")
                st.markdown(result["comparison_table_markdown"])

                st.subheader(f"Papers ({len(result['papers'])})")
                for p in result["papers"]:
                    with st.expander(f"{p['title']} ({p.get('year', 'n/a')})"):
                        st.write(", ".join(p["authors"]) or "Unknown authors")
                        if p.get("url"):
                            st.write(p["url"])
                        st.write("**Summary:**", p["summary"])
            else:
                st.warning(result.get("message", "No results."))

with tab_dashboard:
    st.caption("Illustrative for now — real counts from the RAG store, "
               "grows as queries are run. Fuller analytics: Phase 3.")
    if st.button("Refresh dashboard"):
        pass  # button just forces a rerun
    try:
        resp = requests.get(f"{BACKEND_URL}/dashboard/activity", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        col1, col2 = st.columns(2)
        col1.metric("Papers indexed", data["total_papers_indexed"])

        topics = data["queries_by_topic"]
        if topics:
            df = pd.DataFrame(topics, columns=["Topic", "Papers"])
            col2.bar_chart(df.set_index("Topic"))
        else:
            st.write("No queries yet — run one in the first tab.")
    except requests.exceptions.ConnectionError:
        st.error("Backend not reachable. Start it with: uvicorn backend.main:app --reload")
