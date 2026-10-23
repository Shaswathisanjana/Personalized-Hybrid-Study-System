from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from google import genai

from app.research_agent.models import (
    ResearchEvidenceItem,
    ResearchPaper,
    ResearchSynthesis,
)


class ResearchSynthesizer:
    """
    Produces a student-facing research synthesis using
    ONLY evidence extracted from retrieved scholarly text.

    Gemini is used for organization and explanation,
    not as the evidence source.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
    ):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found in .env"
            )

        self.model_name = model_name

        self.client = genai.Client(
            api_key=api_key
        )

    def synthesize(
        self,
        topic: str,
        question: str,
        evidence: list[ResearchEvidenceItem],
        papers: list[ResearchPaper],
    ) -> ResearchSynthesis:
        """
        Create a grounded research answer.

        The generated answer must rely only on the supplied
        evidence items.
        """

        topic = topic.strip()
        question = question.strip()

        if not topic:
            raise ValueError(
                "Research topic cannot be empty"
            )

        if not question:
            raise ValueError(
                "Research question cannot be empty"
            )

        if not evidence:
            raise ValueError(
                "Cannot synthesize research without evidence"
            )

        evidence_block = self._build_evidence_block(
            evidence
        )

        prompt = f"""
You are the synthesis component of an educational
Research Agent.

TOPIC:
{topic}

STUDENT QUESTION:
{question}

VERIFIED EXTRACTED EVIDENCE:
{evidence_block}

Write a clear explanation answering the student's
question.

STRICT GROUNDING RULES:

1. Use ONLY the evidence supplied above.
2. Do not add facts from your general knowledge.
3. Do not invent study results, statistics, methods,
   participants, conclusions, or comparisons.
4. If the evidence supports only part of the question,
   explicitly say that the available evidence does not
   establish the remaining part.
5. Do not exaggerate a claim beyond what the evidence says.
6. Keep the explanation understandable to a student.
7. When useful, identify which numbered evidence item
   supports a statement.
8. Do not create fake citations or URLs.

Return ONLY valid JSON:

{{
  "answer": "grounded student-facing synthesis",
  "evidence_used": [1, 2]
}}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        text = response.text

        if not text:
            raise RuntimeError(
                "Gemini returned an empty synthesis"
            )

        cleaned = self._clean_json_response(
            text
        )

        try:
            data = json.loads(
                cleaned
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned invalid synthesis JSON"
            ) from exc

        answer = str(
            data.get(
                "answer",
                "",
            )
        ).strip()

        if not answer:
            raise RuntimeError(
                "Generated synthesis answer was empty"
            )

        raw_indices = data.get(
            "evidence_used",
            [],
        )

        used_evidence = self._resolve_used_evidence(
            evidence=evidence,
            raw_indices=raw_indices,
        )

        # If the model gives an answer but fails to return
        # usable evidence indices, retain all supplied
        # evidence rather than creating fake attribution.
        if not used_evidence:
            used_evidence = list(
                evidence
            )

        papers_used = self._find_used_papers(
            evidence=used_evidence,
            papers=papers,
        )

        return ResearchSynthesis(
            topic=topic,
            question=question,
            answer=answer,
            evidence=used_evidence,
            papers_used=papers_used,
        )

    @staticmethod
    def _build_evidence_block(
        evidence: list[ResearchEvidenceItem],
    ) -> str:

        sections: list[str] = []

        for index, item in enumerate(
            evidence,
            start=1,
        ):
            sections.append(
                (
                    f"[Evidence {index}]\n"
                    f"Claim: {item.claim}\n"
                    f"Paper: {item.paper_title}\n"
                    f"URL: {item.paper_url}\n"
                    f"Relevance: {item.relevance}"
                )
            )

        return "\n\n".join(
            sections
        )

    @staticmethod
    def _resolve_used_evidence(
        evidence: list[ResearchEvidenceItem],
        raw_indices,
    ) -> list[ResearchEvidenceItem]:

        if not isinstance(
            raw_indices,
            list,
        ):
            return []

        selected: list[
            ResearchEvidenceItem
        ] = []

        seen: set[int] = set()

        for raw_index in raw_indices:

            try:
                index = int(
                    raw_index
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            # Evidence numbering presented to Gemini
            # starts from 1.
            zero_based = index - 1

            if not (
                0
                <= zero_based
                < len(evidence)
            ):
                continue

            if zero_based in seen:
                continue

            seen.add(
                zero_based
            )

            selected.append(
                evidence[
                    zero_based
                ]
            )

        return selected

    @staticmethod
    def _find_used_papers(
        evidence: list[ResearchEvidenceItem],
        papers: list[ResearchPaper],
    ) -> list[ResearchPaper]:

        used_titles = {
            item.paper_title.strip().lower()
            for item in evidence
        }

        used_urls = {
            item.paper_url.strip()
            for item in evidence
            if item.paper_url.strip()
        }

        selected: list[
            ResearchPaper
        ] = []

        seen: set[str] = set()

        for paper in papers:

            title_match = (
                paper.title.strip().lower()
                in used_titles
            )

            url_match = (
                bool(
                    paper.url.strip()
                )
                and paper.url.strip()
                in used_urls
            )

            if not (
                title_match
                or url_match
            ):
                continue

            identity = (
                paper.paper_id
                or paper.url
                or paper.title.lower()
            )

            if identity in seen:
                continue

            seen.add(
                identity
            )

            selected.append(
                paper
            )

        return selected

    @staticmethod
    def _clean_json_response(
        text: str,
    ) -> str:

        cleaned = text.strip()

        if cleaned.startswith(
            "```"
        ):
            lines = (
                cleaned.splitlines()
            )

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1]
                .strip()
                .startswith("```")
            ):
                lines = lines[:-1]

            cleaned = (
                "\n".join(
                    lines
                ).strip()
            )

        return cleaned