from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AbstractQualityResult:
    is_usable: bool
    status: str
    reason: str
    word_count: int


class AbstractQualityValidator:
    """
    Checks whether a retrieved abstract contains enough
    meaningful text for evidence-grounded research analysis.

    This is a heuristic quality filter, not a scientific
    assessment of a paper's academic quality.
    """

    MIN_WORDS = 40

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(
            r"\s+",
            " ",
            (text or "").strip().lower(),
        )

    def validate(
        self,
        abstract: str,
        title: str = "",
    ) -> AbstractQualityResult:

        normalized = self._normalize(abstract)
        normalized_title = self._normalize(title)

        words = re.findall(
            r"\b[\w'-]+\b",
            normalized,
        )

        word_count = len(words)

        if not normalized:

            return AbstractQualityResult(
                is_usable=False,
                status="reject",
                reason="The source contains no abstract.",
                word_count=0,
            )

        if normalized_title:

            remainder = normalized

            if remainder.startswith(normalized_title):
                remainder = remainder[
                    len(normalized_title):
                ].strip(" -:.,0123456789")

            if not remainder:

                return AbstractQualityResult(
                    is_usable=False,
                    status="reject",
                    reason=(
                        "The retrieved abstract only repeats "
                        "the paper title or a title-like placeholder."
                    ),
                    word_count=word_count,
                )

        placeholder_phrases = {
            "abstract not available",
            "no abstract available",
            "abstract unavailable",
            "not available",
            "no abstract",
        }

        if normalized.strip(" .:-") in placeholder_phrases:

            return AbstractQualityResult(
                is_usable=False,
                status="reject",
                reason="The source contains an abstract placeholder.",
                word_count=word_count,
            )

        if word_count < self.MIN_WORDS:

            return AbstractQualityResult(
                is_usable=False,
                status="review",
                reason=(
                    f"Only {word_count} words were retrieved. "
                    "There is insufficient source context for "
                    "reliable detailed analysis."
                ),
                word_count=word_count,
            )

        return AbstractQualityResult(
            is_usable=True,
            status="accept",
            reason=(
                "The abstract passes the minimum text-quality checks."
            ),
            word_count=word_count,
        )
