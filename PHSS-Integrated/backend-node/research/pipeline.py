"""Evidence-backed research pipeline powered by PHSS_Research_Agent."""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

# Add the vendor PHSS_Research_Agent and original repo to python path
ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
AGENT_PATH = PROJECT_ROOT / "backend-python" / "vendor" / "phss_research_agent"
SRC_PATH = AGENT_PATH / "src"

if str(AGENT_PATH) not in sys.path:
    sys.path.insert(0, str(AGENT_PATH))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(PROJECT_ROOT / "PHSS_Research_Agent") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "PHSS_Research_Agent"))


def atomic_write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def update_status(output_dir: Path, phase: str, **extra):
    status_file = output_dir / "status.json"
    data = {
        "phase": phase,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    atomic_write(status_file, data)


def parse_synthesized_gaps(synthesis_text: str, clusters: list) -> list:
    """Extract structured gaps list compatible with web dashboard display."""
    gaps = []
    if not synthesis_text:
        # Fallback to evidence clusters if synthesis text is unavailable
        for idx, cluster in enumerate(clusters[:5], 1):
            evidence = cluster.get("evidence", [])
            evidence_ids = [e.get("paper_title", f"Paper {e.get('paper_index', idx)}") for e in evidence[:3]]
            snippets = [e.get("sentence", "") for e in evidence[:2]]
            gaps.append({
                "title": f"Limitation Theme {cluster.get('cluster_id', idx)}",
                "rationale": " ".join(snippets) or "Cluster of author-stated limitations across analyzed papers.",
                "research_question": f"How can existing methods overcome {snippets[0][:100] if snippets else 'these cross-paper constraints'}?",
                "proposed_experiment": "Empirically evaluate proposed architecture against cited limitations on benchmark datasets.",
                "evidence_ids": evidence_ids or [f"Cluster {idx}"],
            })
        return gaps

    blocks = re.split(r"RESEARCH GAP \d+", synthesis_text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        title_match = re.search(r"Potential Gap:\s*(.*?)(?=\n\s*(?:Underlying Issue|Evidence|Why This|Gap Type)|$)", block, re.DOTALL | re.IGNORECASE)
        issue_match = re.search(r"Underlying Issue:\s*(.*?)(?=\n\s*(?:Evidence|Why This|Gap Type)|$)", block, re.DOTALL | re.IGNORECASE)
        why_match = re.search(r"Why This Represents an Under-Explored Area:\s*(.*?)(?=\n\s*(?:Gap Type|RESEARCH DIRECTIONS)|$)", block, re.DOTALL | re.IGNORECASE)
        evidence_matches = re.findall(r"[•\-*]\s*(.*?)(?=\n\s*[•\-*]|\n\s*(?:Why This|Gap Type)|$)", block, re.DOTALL)

        title = (title_match.group(1).strip() if title_match else "").split("\n")[0][:200]
        rationale = (issue_match.group(1).strip() if issue_match else "") or (why_match.group(1).strip() if why_match else "")
        question = f"How can we address: {title}?" if title else "What novel methodology overcomes this constraint?"
        experiment = why_match.group(1).strip() if why_match else "Conduct comparative benchmark testing to validate improved generalization."

        evidence_ids = []
        for em in evidence_matches:
            cleaned = " ".join(em.split())[:120]
            if cleaned:
                evidence_ids.append(cleaned)

        if title or rationale:
            gaps.append({
                "title": title or "Identified Research Gap",
                "rationale": rationale or "Synthesized from cross-paper limitation evidence.",
                "research_question": question,
                "proposed_experiment": experiment,
                "evidence_ids": evidence_ids or ["Multi-paper evidence synthesis"],
            })

    if not gaps and clusters:
        for idx, cluster in enumerate(clusters[:3], 1):
            ev = cluster.get("evidence", [])
            gaps.append({
                "title": f"Cross-Paper Challenge {idx}",
                "rationale": ev[0].get("sentence", "Identified limitation") if ev else "Evidence cluster",
                "research_question": "Does this limitation hold across modern architectures?",
                "proposed_experiment": "Replicate evaluation with ablation studies.",
                "evidence_ids": [e.get("paper_title", "Paper") for e in ev[:3]],
            })

    return gaps


def main():
    parser = argparse.ArgumentParser(description="Run PHSS Research Agent worker pipeline.")
    parser.add_argument("--topic", required=True, help="Research topic string")
    parser.add_argument("--count", type=int, default=5, help="Number of papers to analyze")
    parser.add_argument("--output", required=True, help="Output directory path")
    args = parser.parse_args()

    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PHSS_RESEARCH_OUTPUT_DIR"] = str(output_dir)
    import src.config as agent_config
    agent_config.OUTPUT_DIR = output_dir
    import src.report_generator as rep_gen_mod
    rep_gen_mod.OUTPUT_DIR = output_dir
    from src.research_agent import ResearchAgent

    try:
        update_status(output_dir, "planning_and_searching", topic=args.topic, count=args.count)

        agent = ResearchAgent()
        update_status(output_dir, "downloading_and_analyzing_papers")
        report = agent.run(topic=args.topic, max_papers=args.count, generate_docx=True)

        update_status(output_dir, "synthesizing_results")

        # Ensure gaps key is attached for UI compatibility
        synthesis_text = report.get("research_gap_synthesis") or ""
        clusters = report.get("semantic_evidence_clusters") or []
        report["gaps"] = parse_synthesized_gaps(synthesis_text, clusters)

        # Write latest_report.json to output directory
        latest_report_path = output_dir / "latest_report.json"
        with open(latest_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        # Ensure both docx filenames exist in the directory
        docx_candidates = [
            output_dir / "research_literature_report.docx",
            output_dir / "research_report.docx",
        ]
        lit_doc = output_dir / "research_literature_report.docx"
        rep_doc = output_dir / "research_report.docx"
        if lit_doc.is_file() and not rep_doc.is_file():
            shutil.copyfile(lit_doc, rep_doc)
        elif rep_doc.is_file() and not lit_doc.is_file():
            shutil.copyfile(rep_doc, lit_doc)

        update_status(output_dir, "completed")
        print(f"[pipeline] PHSS Research Agent completed successfully. Report saved to {output_dir}")
    except Exception as exc:
        print(f"[pipeline] Error during research pipeline: {exc}", file=sys.stderr)
        update_status(output_dir, "failed", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
