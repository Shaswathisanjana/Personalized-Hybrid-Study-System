"""Download adapter for PHSS-Unified's original WordResearchReportGenerator."""
import sys
import tempfile
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parents[3] / "vendor" / "phss_research_agent"

def export_word_report(report_data):
    if not isinstance(report_data,dict):
        raise ValueError("A research report is required.")
    data=report_data.get("research") if isinstance(report_data.get("research"),dict) else report_data
    if str(VENDOR_DIR) not in sys.path:
        sys.path.insert(0,str(VENDOR_DIR))
    from src.report_generator import WordResearchReportGenerator

    analyses=[]
    for row in data.get("paper_analyses") or data.get("papers") or []:
        if not isinstance(row,dict):
            continue
        item=dict(row)
        for destination,source in [("dataset","datasets"),("results_metrics","results"),("author_stated_limitations","limitations")]:
            if destination not in item and source in item:
                item[destination]=item[source]
        item.setdefault("year",str(item.get("published") or "")[:4])
        analyses.append(item)
    synthesis=data.get("research_gap_synthesis") or ""
    if not isinstance(synthesis,str):
        import json
        synthesis=json.dumps(synthesis,ensure_ascii=False,default=str)
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
