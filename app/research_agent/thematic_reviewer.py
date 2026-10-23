from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from google import genai

from app.research_agent.paper_summarizer import (
    PaperSummary,
    SUMMARY_FIELDS,
    NOT_REPORTED,
)


@dataclass
class ThemeEvidence:
    paper_index: int
    paper_title: str
    paper_url: str
    field_name: str
    finding: str
    source_quote: str


@dataclass
class ResearchTheme:
    name: str
    description: str
    supporting_evidence: list[ThemeEvidence] = field(
        default_factory=list
    )
    coverage: str = ""


@dataclass
class ThematicReview:
    topic: str
    themes: list[ResearchTheme] = field(
        default_factory=list
    )
    papers_analyzed: int = 0
    limitations: list[str] = field(
        default_factory=list
    )


class ThematicReviewError(RuntimeError):
    """Raised when thematic review generation fails."""


class ThematicLiteratureReviewer:
    """
    Groups structured paper summaries into research themes.

    Only summaries with source-backed fields are supplied
    to Gemini. Returned paper references are checked
    against the supplied summaries.
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

            self.client = genai.Client(api_key=api_key)

    @staticmethod
    def _clean_json(text: str) -> str:
        cleaned = text.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()[1:]

            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        return cleaned

    @staticmethod
    def _build_source_data(
        summaries: list[PaperSummary],
    ) -> list[dict]:

        source_data = []

        for index, summary in enumerate(summaries, start=1):
            supported_fields = {}

            for name in SUMMARY_FIELDS:
                value = getattr(summary, name)
                quote = summary.evidence_quotes.get(name, "")

                if value == NOT_REPORTED or not quote:
                    continue

                supported_fields[name] = {
                    "value": value,
                    "source_quote": quote,
                }

            source_data.append({
                "paper_index": index,
                "title": summary.title,
                "url": summary.source_url,
                "year": summary.year,
                "supported_fields": supported_fields,
            })

        return source_data

    def review(
        self,
        topic: str,
        summaries: list[PaperSummary],
        max_themes: int = 5,
    ) -> ThematicReview:

        topic = topic.strip()

        if not topic:
            raise ValueError("topic cannot be empty")

        if len(summaries) < 2:
            raise ValueError(
                "At least two paper summaries are required"
            )

        if not 1 <= max_themes <= 10:
            raise ValueError(
                "max_themes must be between 1 and 10"
            )

        source_data = self._build_source_data(summaries)

        review = ThematicReview(
            topic=topic,
            papers_analyzed=len(summaries),
            limitations=[
                "Analysis is based on supplied structured "
                "summaries derived from abstracts, not full papers."
            ],
        )

        if not any(
            paper["supported_fields"]
            for paper in source_data
        ):
            review.limitations.append(
                "No source-backed summary fields were available."
            )
            return review

        prompt = f"""
You are preparing a thematic literature review.

TOPIC:
{topic}

SOURCE DATA:
{json.dumps(source_data, ensure_ascii=False, indent=2)}

Identify at most {max_themes} meaningful research themes.

RULES:
1. Use ONLY the supplied supported_fields.
2. Do not invent papers, datasets, results or citations.
3. Group similar findings when justified.
4. A theme may be supported by one or multiple papers.
5. Never claim that all papers agree unless the supplied
   evidence establishes this.
6. For every theme, give its supporting paper_index and
   exact field_name from the supplied data.
7. A theme description must not go beyond the cited findings.
8. Do not confuse proposed methods with demonstrated results.
9. Return ONLY valid JSON.

FORMAT:
{{
  "themes": [
    {{
      "name": "Theme name",
      "description": "Evidence-grounded description",
      "supports": [
        {{
          "paper_index": 1,
          "field_name": "proposed_method"
        }}
      ]
    }}
  ]
}}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            if not response.text:
                raise ThematicReviewError(
                    "Gemini returned an empty response"
                )

            data = json.loads(
                self._clean_json(response.text)
            )

        except ThematicReviewError:
            raise

        except Exception as exc:
            raise ThematicReviewError(
                f"Thematic review generation failed: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ThematicReviewError(
                "Expected a JSON object"
            )

        raw_themes = data.get("themes", [])

        if not isinstance(raw_themes, list):
            raise ThematicReviewError(
                "themes must be a list"
            )

        for raw_theme in raw_themes[:max_themes]:

            if not isinstance(raw_theme, dict):
                continue

            name = raw_theme.get("name", "")
            description = raw_theme.get("description", "")
            raw_supports = raw_theme.get("supports", [])

            if (
                not isinstance(name, str)
                or not name.strip()
                or not isinstance(description, str)
                or not description.strip()
                or not isinstance(raw_supports, list)
            ):
                continue

            evidence = []
            seen = set()

            for support in raw_supports:

                if not isinstance(support, dict):
                    continue

                index = support.get("paper_index")
                field_name = support.get("field_name")

                if type(index) is not int:
                    continue

                if not 1 <= index <= len(summaries):
                    continue

                if field_name not in SUMMARY_FIELDS:
                    continue

                identity = (index, field_name)

                if identity in seen:
                    continue

                summary = summaries[index - 1]
                finding = getattr(summary, field_name)
                quote = summary.evidence_quotes.get(
                    field_name, ""
                )

                if finding == NOT_REPORTED or not quote:
                    continue

                seen.add(identity)

                evidence.append(
                    ThemeEvidence(
                        paper_index=index,
                        paper_title=summary.title,
                        paper_url=summary.source_url,
                        field_name=field_name,
                        finding=finding,
                        source_quote=quote,
                    )
                )

            if not evidence:
                continue

            unique_papers = {
                item.paper_index
                for item in evidence
            }

            coverage = (
                "Cross-paper theme"
                if len(unique_papers) >= 2
                else "Single-paper observation"
            )

            review.themes.append(
                ResearchTheme(
                    name=name.strip(),
                    description=description.strip(),
                    supporting_evidence=evidence,
                    coverage=coverage,
                )
            )

        if not review.themes:
            review.limitations.append(
                "No themes with valid source references "
                "were generated."
            )

        return review
