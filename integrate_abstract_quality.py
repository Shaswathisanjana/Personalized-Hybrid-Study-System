from pathlib import Path

path = Path("app/research_agent/research_workflow.py")
source = path.read_text(encoding="utf-8-sig")

backup = Path("app/research_agent/research_workflow_before_abstract_filter.py.bak")

import_anchor = "from app.research_agent.models import ResearchPaper\n"

fields_anchor = (
    "    papers: list[ResearchPaper] = field(default_factory=list)\n"
    "    summaries: list[PaperSummary] = field(default_factory=list)\n"
)

workflow_anchor = (
    "        summarizer = (\n"
    "            self.summarizer\n"
    "            if self.summarizer is not None\n"
    "            else StructuredPaperSummarizer()\n"
    "        )\n\n"
    "        result.summaries = summarizer.summarize_multiple(\n"
    "            result.papers\n"
    "        )"
)

anchors = (import_anchor, fields_anchor, workflow_anchor)

if not all(source.count(anchor) == 1 for anchor in anchors):
    raise RuntimeError(
        "Expected workflow structure not found exactly once. "
        "No changes were made."
    )

if "AbstractQualityValidator" in source:
    raise RuntimeError(
        "Abstract validation already appears integrated. "
        "No changes were made."
    )

backup.write_text(source, encoding="utf-8")

source = source.replace(
    import_anchor,
    import_anchor
    + "from app.research_agent.abstract_quality_validator import (\n"
    + "    AbstractQualityValidator,\n"
    + "    AbstractQualityResult,\n"
    + ")\n",
    1,
)

source = source.replace(
    fields_anchor,
    (
        "    papers: list[ResearchPaper] = field(default_factory=list)\n"
        "    accepted_papers: list[ResearchPaper] = field(default_factory=list)\n"
        "    excluded_papers: list[tuple[ResearchPaper, AbstractQualityResult]] = field(default_factory=list)\n"
        "    summaries: list[PaperSummary] = field(default_factory=list)\n"
    ),
    1,
)

replacement = (
    "        validator = AbstractQualityValidator()\n\n"
    "        for paper in result.papers:\n"
    "            quality = validator.validate(\n"
    "                abstract=paper.abstract,\n"
    "                title=paper.title,\n"
    "            )\n\n"
    "            if quality.is_usable:\n"
    "                result.accepted_papers.append(paper)\n"
    "            else:\n"
    "                result.excluded_papers.append((paper, quality))\n"
    "                result.warnings.append(\n"
    "                    f\"Excluded paper '{paper.title}': {quality.reason}\"\n"
    "                )\n\n"
    "        if not result.accepted_papers:\n"
    "            result.warnings.append(\n"
    "                'No papers passed abstract quality validation. '\n"
    "                'Detailed analysis was not performed.'\n"
    "            )\n"
    "            return result\n\n"
    "        summarizer = (\n"
    "            self.summarizer\n"
    "            if self.summarizer is not None\n"
    "            else StructuredPaperSummarizer()\n"
    "        )\n\n"
    "        result.summaries = summarizer.summarize_multiple(\n"
    "            result.accepted_papers\n"
    "        )"
)

source = source.replace(workflow_anchor, replacement, 1)

path.write_text(source, encoding="utf-8")

print("SUCCESS: Abstract quality filtering integrated.")
print("BACKUP:", backup)
