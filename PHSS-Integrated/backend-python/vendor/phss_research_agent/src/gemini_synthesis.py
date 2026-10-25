
import os
import time

from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    Groq = None

from .config import GROQ_MODEL

load_dotenv()


class GeminiSynthesizer:
    """Synthesize research gaps from BGE-derived evidence using Groq."""

    def __init__(self):
        key = os.getenv("GROQ_API_KEY")

        if not key or Groq is None:
            self.client = None
            return

        self.client = Groq(api_key=key)

    def synthesize(
        self,
        topic,
        papers,
        evidence_clusters,
    ):
        if not self.client:
            print(
                "  Groq API key or SDK not available. "
                "Set GROQ_API_KEY and install groq."
            )
            return None

        # ---------------------------------------------------------
        # BUILD EVIDENCE TEXT FROM BGE-DERIVED CLUSTERS
        # ---------------------------------------------------------

        cluster_sections = []

        for cluster in evidence_clusters:
            evidence_lines = []

            for evidence in cluster.get("evidence", []):
                evidence_lines.append(
                    f"""
- Evidence:
  {evidence.get("sentence", "")}

  Supporting paper:
  {evidence.get("paper_title", "Unknown")}

  Semantic relevance:
  {evidence.get("relevance", "Not available")}
"""
                )

            cluster_text = f"""
==================================================
SEMANTIC EVIDENCE CLUSTER {cluster.get("cluster_id", "?")}
==================================================

Evidence count:
{cluster.get("evidence_count", 0)}

Unique supporting papers:
{cluster.get("unique_paper_count", 0)}

Average topic relevance:
{cluster.get("average_relevance", "Not available")}

Recurrence factor:
{cluster.get("recurrence_factor", "Not available")}

Supporting evidence:
{"".join(evidence_lines)}
"""
            cluster_sections.append(cluster_text)

        evidence_text = "\n".join(cluster_sections)

        if not evidence_text.strip():
            print("  No evidence clusters available for synthesis.")
            return None

        # ---------------------------------------------------------
        # RESEARCH-GAP SYNTHESIS PROMPT
        # ---------------------------------------------------------

        prompt = f"""
You are the research-gap synthesis component
of an academic research assistant.

Research topic:
{topic}

The system has already performed semantic analysis
using BGE embeddings.

The evidence below was produced by:

1. Limitation/challenge evidence extraction
2. BGE semantic embeddings
3. Cosine similarity
4. Semantic clustering
5. Topic relevance analysis
6. Cross-paper evidence comparison

Your task is NOT to independently search for research gaps.

Instead, synthesize potential research gaps ONLY
from the evidence provided below.

SEMANTIC EVIDENCE CLUSTERS:

{evidence_text}

TASK:

For each strong evidence cluster:

1. Identify the underlying research issue.
2. Compare evidence across the supporting papers.
3. Determine whether the evidence indicates:
   - a recurring limitation
   - an under-explored area
   - a missing combination of approaches
   - insufficient evaluation
   - dataset limitations
   - generalization limitations
   - computational limitations
   - robustness limitations
   - or another clearly supported issue
4. Formulate a potential research gap.
5. Explain why the evidence suggests that the area
   may be under-explored.
6. List the supporting papers.

STRICT RULES:

- Do NOT invent information.
- Do NOT introduce methods, datasets, results,
  or limitations absent from the evidence.
- Do NOT claim definite novelty.
- Use "potential research gap" or "under-explored area".
- High relevance alone is not proof of a research gap.
- Prefer evidence supported by multiple papers.
- Ignore clusters clearly irrelevant to the topic.
- Do not simply copy one limitation sentence.
- Synthesize evidence into a higher-level research issue.
- If evidence is insufficient, do not force a gap.
- Distinguish evidence from interpretation.

OUTPUT FORMAT:

RESEARCH GAP 1

Potential Gap:
<coherent synthesized research-gap statement>

Underlying Issue:
<underlying limitation or under-explored area>

Evidence:
• <paper> — <relevant evidence>
• <paper> — <relevant evidence>
• <paper> — <relevant evidence>

Why This Represents an Under-Explored Area:
<brief evidence-based explanation>

Gap Type:
<dataset / generalization / methodology / evaluation /
computational / robustness / missing combination / other>

Continue only for strong evidence-supported gaps.

RESEARCH DIRECTIONS

1. <research direction derived from gap 1>
2. <research direction derived from gap 2>
3. <research direction derived from gap 3>

If no strong gaps are supported, state that explicitly.
"""

        # ---------------------------------------------------------
        # GROQ REQUEST WITH RETRIES
        # ---------------------------------------------------------

        for attempt in range(3):
            try:
                print(
                    f"  Calling Groq ({GROQ_MODEL})..."
                )

                response = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an academic research-gap "
                                "synthesis assistant. Use only the "
                                "provided evidence. Never invent "
                                "findings or claim verified novelty."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.1,
                    max_tokens=3500,
                )

                result = response.choices[0].message.content

                if result and result.strip():
                    return result.strip()

                print("  Groq returned an empty response.")
                return None

            except Exception as exc:
                error_text = str(exc).lower()

                retryable = any(
                    marker in error_text
                    for marker in (
                        "429",
                        "rate limit",
                        "503",
                        "unavailable",
                        "timeout",
                        "timed out",
                        "500",
                        "502",
                        "504",
                    )
                )

                if not retryable:
                    print("  Groq error:", exc)
                    return None

                if attempt < 2:
                    wait_time = 5 * (attempt + 1)

                    print(
                        "  Groq temporarily unavailable or rate-limited. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                else:
                    print(
                        "  Groq failed after 3 attempts:",
                        exc,
                    )
                    return None

        return None
