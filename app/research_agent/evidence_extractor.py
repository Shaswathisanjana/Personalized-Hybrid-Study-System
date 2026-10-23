from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from google import genai

from app.research_agent.models import (
    ResearchEvidenceItem,
    ResearchPaper,
)
from app.research_agent.semantic_ranker import (
    SemanticRankedPaper,
)


class ResearchEvidenceExtractor:
    """
    Extracts grounded research claims from retrieved
    scholarly papers.

    Important:
    - Papers must already have been retrieved.
    - The model receives only supplied paper metadata/text.
    - Extracted claims must be supported by that text.
    - The model is not allowed to invent missing findings.
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

    def extract_from_ranked_papers(
        self,
        question: str,
        ranked_papers: list[SemanticRankedPaper],
        max_claims_per_paper: int = 2,
    ) -> list[ResearchEvidenceItem]:
        """
        Extract grounded claims from multiple ranked papers.
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "Research question cannot be empty"
            )

        if max_claims_per_paper <= 0:
            raise ValueError(
                "max_claims_per_paper must be greater than zero"
            )

        evidence: list[ResearchEvidenceItem] = []

        for ranked in ranked_papers:

            paper_evidence = self.extract_from_paper(
                question=question,
                paper=ranked.paper,
                paper_relevance=ranked.semantic_score,
                max_claims=max_claims_per_paper,
            )

            evidence.extend(
                paper_evidence
            )

        return evidence

    def extract_from_paper(
        self,
        question: str,
        paper: ResearchPaper,
        paper_relevance: float,
        max_claims: int = 2,
    ) -> list[ResearchEvidenceItem]:
        """
        Extract claims supported by one paper's supplied
        title and abstract.
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "Research question cannot be empty"
            )

        if max_claims <= 0:
            raise ValueError(
                "max_claims must be greater than zero"
            )

        paper_relevance = max(
            0.0,
            min(1.0, paper_relevance),
        )

        abstract = (
            paper.abstract.strip()
            if paper.abstract
            else ""
        )

        # We should not pretend to extract findings when
        # there is no usable scholarly text.
        if (
            not abstract
            or abstract.lower() == "not available"
        ):
            return []

        prompt = f"""
You are extracting grounded evidence from an academic
paper for a student's research question.

STUDENT RESEARCH QUESTION:
{question}

PAPER TITLE:
{paper.title}

PAPER ABSTRACT:
{abstract}

Your job is to extract at most {max_claims} claims that:

1. Are directly supported by the supplied abstract.
2. Are relevant to the student's research question.
3. Do not contain information that is absent from the
   supplied abstract.
4. Do not invent methods, results, sample sizes,
   statistics, conclusions, or findings.
5. Can stand as concise evidence statements.

If the abstract does not provide useful evidence for the
question, return an empty list.

For each claim, also provide a relevance score from
0.0 to 1.0 representing how directly that claim helps
answer the student's research question.

Return ONLY valid JSON in this structure:

{{
  "claims": [
    {{
      "claim": "claim supported by the abstract",
      "relevance": 0.0
    }}
  ]
}}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )

            text = response.text

            if not text:
                return []

            cleaned = self._clean_json_response(
                text
            )

            data = json.loads(
                cleaned
            )

            raw_claims = data.get(
                "claims",
                [],
            )

            if not isinstance(
                raw_claims,
                list,
            ):
                return []

            evidence: list[
                ResearchEvidenceItem
            ] = []

            for item in raw_claims[
                :max_claims
            ]:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                claim = str(
                    item.get(
                        "claim",
                        "",
                    )
                ).strip()

                if not claim:
                    continue

                try:
                    claim_relevance = float(
                        item.get(
                            "relevance",
                            0.0,
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    continue

                claim_relevance = max(
                    0.0,
                    min(
                        1.0,
                        claim_relevance,
                    ),
                )

                # Combine:
                # - relevance of the paper itself
                # - relevance of this particular claim
                #
                # This is currently a heuristic confidence
                # signal, not a scientifically calibrated
                # probability.
                final_relevance = (
                    paper_relevance
                    * claim_relevance
                )

                evidence.append(
                    ResearchEvidenceItem(
                        claim=claim,
                        paper_title=paper.title,
                        paper_url=paper.url,
                        relevance=round(
                            final_relevance,
                            3,
                        ),
                    )
                )

            return evidence

        except Exception as exc:
            print(
                "Evidence extraction skipped for "
                f"'{paper.title}' because "
                f"{type(exc).__name__}: {exc}"
            )

            return []

    @staticmethod
    def _clean_json_response(
        text: str,
    ) -> str:
        """
        Remove Markdown code fences when present.
        """

        cleaned = text.strip()

        if cleaned.startswith("```"):

            lines = cleaned.splitlines()

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
                "\n".join(lines).strip()
            )

        return cleaned