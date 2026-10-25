from pathlib import Path
import json

import streamlit as st

from src.config import OUTPUT_DIR
from src.research_agent import ResearchAgent
from src.uploaded_pdf_analysis import analyze_uploaded_pdfs, MAX_PDF_COUNT, MAX_PDF_SIZE_BYTES

st.set_page_config(
    page_title="PHSS Research Agent",
    page_icon="📚",
    layout="wide",
)

OUTPUT_DIR = Path(OUTPUT_DIR).resolve()
WORD_REPORT_PATH = OUTPUT_DIR / "research_literature_report.docx"
JSON_REPORT_PATH = OUTPUT_DIR / "latest_report.json"

st.title("📚 PHSS Research Agent")
st.write(
    "Analyze research papers, compare methodologies and results, "
    "and identify potential research gaps."
)

mode = st.radio(
    "Choose research mode",
    ["Search arXiv", "Upload PDFs"],
    horizontal=True,
    help="Use arXiv retrieval or analyze your own collection of up to 15 PDFs.",
)

if mode == "Search arXiv":
    with st.form("research_form"):
        topic = st.text_area(
            "Research topic",
            placeholder="Example: PCB defect detection using deep learning",
            height=100,
        )
        max_papers = st.number_input(
            "Number of papers to analyze",
            min_value=1,
            max_value=10,
            value=5,
            step=1,
        )
        submitted = st.form_submit_button(
            "Start Research", type="primary", use_container_width=True
        )

    if submitted:
        if not topic.strip():
            st.error("Please enter a research topic.")
        else:
            try:
                with st.spinner(f"Searching and analyzing up to {max_papers} papers..."):
                    agent = ResearchAgent()
                    agent.run(topic=topic.strip(), max_papers=int(max_papers), generate_docx=True)
                st.session_state["research_completed"] = True
                st.session_state["research_topic"] = topic.strip()
                st.session_state["research_mode_completed"] = "arxiv"
                st.success("Research pipeline completed.")
            except Exception as exc:
                st.session_state["research_completed"] = False
                st.error(f"Research failed: {exc}")
                st.exception(exc)

    if st.session_state.get("research_completed") and st.session_state.get("research_mode_completed") == "arxiv":
        st.subheader("Download Research Results")
        st.write(f"**Topic:** {st.session_state.get('research_topic', '')}")
        if JSON_REPORT_PATH.is_file():
            try:
                latest_payload = json.loads(JSON_REPORT_PATH.read_text(encoding="utf-8"))
                agentic = latest_payload.get("agentic_controller", {})
                if agentic.get("enabled"):
                    with st.expander("View agentic research decisions", expanded=True):
                        retrieval = agentic.get("retrieval_evaluation", {})
                        extraction = agentic.get("extraction_quality", {})
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Papers retrieved", f"{retrieval.get('paper_count', 0)} / {retrieval.get('requested_papers', 0)}")
                        c2.metric("Topic coverage", f"{retrieval.get('topic_token_coverage', 0):.0%}")
                        c3.metric("Field completeness", f"{extraction.get('completeness_ratio', 0):.0%}")
                        st.caption(f"Controller decision: {agentic.get('decision', 'not available')}")
                        trace = agentic.get("trace", [])
                        if trace:
                            st.dataframe(trace, use_container_width=True, hide_index=True)
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                st.info(f"Agentic decision details could not be displayed: {exc}")
        if WORD_REPORT_PATH.is_file():
            st.download_button(
                "📄 Download Word Report",
                data=WORD_REPORT_PATH.read_bytes(),
                file_name="research_literature_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        else:
            st.warning(f"Word report not found at: {WORD_REPORT_PATH}")
        if JSON_REPORT_PATH.is_file():
            st.download_button(
                "📥 Download JSON Results",
                data=JSON_REPORT_PATH.read_bytes(),
                file_name="latest_report.json",
                mime="application/json",
                use_container_width=True,
            )
        else:
            st.info(f"JSON report not found at: {JSON_REPORT_PATH}")

else:
    st.markdown(
        f"Upload up to **{MAX_PDF_COUNT} PDFs**. Only PDFs judged relevant to your topic "
        "will be included in the detailed analysis. For PCB topics, general surface-defect papers without PCB-specific evidence are classified as indirectly relevant and excluded from the core comparison. Other files will be listed in the report."
    )
    with st.form("upload_form"):
        upload_topic = st.text_area(
            "What topic are these PDFs about?",
            placeholder="Example: Glaucoma detection using deep learning",
            height=90,
        )
        uploaded_pdfs = st.file_uploader(
            "Upload research papers (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            help=f"Maximum {MAX_PDF_COUNT} files; maximum {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB per file.",
        )
        relevance_threshold = st.slider(
            "Minimum semantic relevance score",
            min_value=0.15,
            max_value=0.60,
            value=0.30,
            step=0.01,
            help="Higher values are stricter. This score is combined with topic-specific checks; for PCB topics, generic surface-defect papers without PCB evidence are not included in the core analysis.",
        )
        upload_submitted = st.form_submit_button(
            "Check Relevance and Generate Report",
            type="primary",
            use_container_width=True,
        )

    if upload_submitted:
        if not upload_topic.strip():
            st.error("Please enter the topic for the uploaded PDFs.")
        elif not uploaded_pdfs:
            st.error("Please upload at least one PDF.")
        elif len(uploaded_pdfs) > MAX_PDF_COUNT:
            st.error(f"Please upload no more than {MAX_PDF_COUNT} PDFs. You selected {len(uploaded_pdfs)}.")
        else:
            try:
                with st.spinner("Extracting PDF text, checking relevance, and generating the report..."):
                    result = analyze_uploaded_pdfs(
                        topic=upload_topic.strip(),
                        uploaded_files=uploaded_pdfs,
                        min_relevance=float(relevance_threshold),
                    )
                st.session_state["upload_result"] = {
                    "topic": upload_topic.strip(),
                    "decisions": result["decisions"],
                    "docx_bytes": result["docx_path"].read_bytes(),
                    "json_bytes": result["json_path"].read_bytes(),
                    "relevant_count": result["report"].get("number_relevant", 0),
                    "uploaded_count": len(uploaded_pdfs),
                }
                st.success(
                    f"Completed relevance screening: {result['report'].get('number_relevant', 0)} "
                    f"of {len(uploaded_pdfs)} PDFs included in detailed analysis."
                )
            except Exception as exc:
                st.error(f"Uploaded-PDF analysis failed: {exc}")
                st.exception(exc)

    upload_result = st.session_state.get("upload_result")
    if upload_result:
        st.subheader("Uploaded PDF Screening Results")
        st.write(f"**Topic:** {upload_result['topic']}")
        st.write(
            f"**Included:** {upload_result['relevant_count']} / {upload_result['uploaded_count']} PDFs"
        )
        st.dataframe(upload_result["decisions"], use_container_width=True, hide_index=True)
        st.download_button(
            "📄 Download Uploaded-PDF Word Report",
            data=upload_result["docx_bytes"],
            file_name="uploaded_pdf_literature_report.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        st.download_button(
            "📥 Download Uploaded-PDF JSON Results",
            data=upload_result["json_bytes"],
            file_name="uploaded_pdf_report.json",
            mime="application/json",
            use_container_width=True,
        )
