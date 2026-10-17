from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv
from google import genai

from app.research_agent.models import ResearchPaper


NOT_REPORTED = "Not reported in available source"

SUMMARY_FIELDS = (
    "research_problem",
    "proposed_method",
    "dataset",
    "evaluation_metrics",
    "key_findings",
    "limitations",
)


@dataclass
class PaperSummary:
    title: str
    authors: list[str]
    year: int | None
    source_url: str

    research_problem: str = NOT_REPORTED
    proposed_method: str = NOT_REPORTED
    dataset: str = NOT_REPORTED
    evaluation_metrics: str = NOT_REPORTED
    key_findings: str = NOT_REPORTED
    limitations: str = NOT_REPORTED

    evidence_quotes: dict[str, str] = field(
        default_factory=dict
    )

    source_scope: str = "abstract_only"


class PaperSummarizationError(RuntimeError):
    """Raised when structured paper summarization fails."""


class StructuredPaperSummarizer:
    """
    Creates structured summaries using the supplied
    paper abstract only.

    Every reported field must have a supporting quote
    that appears in the supplied abstract.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
        client=None,
    ):
        load_dotenv()

        self.model_name = model_name

        if client is not None:
            self.client = client
        else:
            api_key = os.getenv("GEMINI_API_KEY")

            if not api_key:
                raise ValueError(
                    "GEMINI_API_KEY was not found in .env"
                )

            self.client = genai.Client(
                api_key=api_key
            )

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip().casefold()

    @staticmethod
    def _clean_json(text: str) -> str:
        cleaned = text.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            lines = lines[1:]

            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        return cleaned

    def summarize(
        self,
        paper: ResearchPaper,
    ) -> PaperSummary:

        if not isinstance(paper, ResearchPaper):
            raise TypeError(
                "paper must be a ResearchPaper object"
            )

        summary = PaperSummary(
            title=paper.title,
            authors=list(paper.authors),
            year=paper.year,
            source_url=paper.url,
        )

        abstract = paper.abstract.strip()

        if (
            not abstract
            or abstract.casefold() == "not available"
        ):
            return summary

        fields_description = "\n".join(
            f"- {name}"
            for name in SUMMARY_FIELDS
        )

        prompt = f"""
You are an evidence-grounded academic paper
summarization component.

Use ONLY the supplied paper abstract.

PAPER TITLE:
{paper.title}

ABSTRACT:
{abstract}

Extract these fields:

{fields_description}

For EACH field return:
1. value: a concise explanation supported by the abstract.
2. quote: an EXACT continuous quotation copied from
   the abstract supporting that value.

STRICT RULES:
- Do not use outside knowledge.
- Do not invent datasets, metrics, results or limitations.
- If a field is not explicitly supported, return
  value = "{NOT_REPORTED}" and quote = "".
- Do not treat a proposed method as a proven result.
- Do not invent numerical performance values.
- Limitations must be supported by the abstract.
- Return only valid JSON.

Required JSON structure:

{{
  "research_problem": {{
    "value": "...",
    "quote": "..."
  }},
  "proposed_method": {{
    "value": "...",
    "quote": "..."
  }},
  "dataset": {{
    "value": "...",
    "quote": "..."
  }},
  "evaluation_metrics": {{
    "value": "...",
    "quote": "..."
  }},
  "key_findings": {{
    "value": "...",
    "quote": "..."
  }},
  "limitations": {{
    "value": "...",
    "quote": "..."
  }}
}}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            response_text = response.text

            if not response_text:
                raise PaperSummarizationError(
                    "Gemini returned an empty response"
                )

            data = json.loads(
                self._clean_json(response_text)
            )

        except PaperSummarizationError:
            raise

        except (json.JSONDecodeError, ValueError) as exc:
            raise PaperSummarizationError(
                "Gemini returned invalid summary JSON"
            ) from exc

        except Exception as exc:
            raise PaperSummarizationError(
                f"Paper summarization failed: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise PaperSummarizationError(
                "Expected a JSON object"
            )

        normalized_abstract = self._normalize(
            abstract
        )

        for field_name in SUMMARY_FIELDS:
            item = data.get(field_name, {})

            if not isinstance(item, dict):
                continue

            value = item.get("value", "")
            quote = item.get("quote", "")

            if not isinstance(value, str):
                continue

            if not isinstance(quote, str):
                continue

            value = value.strip()
            quote = quote.strip()

            if (
                not value
                or value.casefold() == NOT_REPORTED.casefold()
                or not quote
            ):
                continue

            # Reject fields without a matching source quote.
            if (
                self._normalize(quote)
                not in normalized_abstract
            ):
                continue

            setattr(
                summary,
                field_name,
                value,
            )

            summary.evidence_quotes[field_name] = quote

        return summary

    def summarize_multiple(
        self,
        papers: list[ResearchPaper],
    ) -> list[PaperSummary]:

        summaries: list[PaperSummary] = []

        for paper in papers:
            try:
                summaries.append(
                    self.summarize(paper)
                )

            except PaperSummarizationError as exc:
                print(
                    f"Skipping '{paper.title}': {exc}"
                )

        return summaries
