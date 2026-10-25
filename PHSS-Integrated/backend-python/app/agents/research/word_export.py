"""Download adapter for PHSS-Unified's original WordResearchReportGenerator."""
import sys
import tempfile
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parents[3] / "vendor" / "phss_research_agent"

def export_word_report(report_data):
    if not isinstance(report_data,dict):
        raise ValueError("A research report is required.")
    data=report_data.get("research") if isinstance(report_data.get("research"),dict) else report_data
    if data.get("review_mode")=="evolution" or isinstance(data.get("research_progression"),dict):
        from app.agents.research.evolution_export import export_progression
        return export_progression(data)
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0,str(VENDOR_DIR))
    from src.report_generator import WordResearchReportGenerator

    from src.provenance import source_key
    selected={source_key(p.get("url") or p.get("pdf_url")):p for p in data.get("papers",[]) if source_key(p.get("url") or p.get("pdf_url"))}
    analyses=[]
    for row in data.get("paper_analyses") or data.get("papers") or []:
        if not isinstance(row,dict):
            continue
        item=dict(row)
        key=source_key(item.get("url") or item.get("pdf_url"))
        if selected and key not in selected:
            raise ValueError("A paper analysis cannot be matched to the selected source list. Start a new review rather than exporting mismatched evidence.")
        metadata=selected.get(key,{})
        if metadata.get("title") and item.get("title")!=metadata["title"]:
            raise ValueError("Paper title and source URL disagree. Regenerate the review.")
        item["source_id"]=metadata.get("source_id") or item.get("source_id") or str(len(analyses)+1)
        item["paper_index"]=len(analyses)+1
        for destination,source in [("dataset","datasets"),("results_metrics","results"),("author_stated_limitations","limitations")]:
            if destination not in item and source in item:
                item[destination]=item[source]
        item.setdefault("year",str(item.get("published") or "")[:4])
        analyses.append(item)
    synthesis=data.get("research_gap_synthesis") or ""
    if not isinstance(synthesis,str):
        import json
        synthesis=json.dumps(synthesis,ensure_ascii=False,default=str)
    import re
    referenced=set(re.findall(r"\[(S\d+)\]",synthesis))
    known={str(row["source_id"]) for row in analyses}
    if not referenced<=known:
        raise ValueError("The report cites sources absent from its reference list. Start a new research review; citation IDs will not be guessed.")
    # Original PHSS-Unified formatting, isolated output per download.
    # Never read a client-provided path or another report's shared output.
    with tempfile.TemporaryDirectory(prefix="phss-unified-report-") as directory:
        generator=WordResearchReportGenerator(output_dir=directory)
        path=generator.generate(
            topic=data.get("topic") or "Research Literature Review",
            paper_analyses=analyses,
            gap_synthesis=synthesis,
            evidence_clusters=data.get("semantic_evidence_clusters") or [],
            output_path=Path(directory)/"research_literature_report.docx",
        )
        return Path(path).read_bytes()
