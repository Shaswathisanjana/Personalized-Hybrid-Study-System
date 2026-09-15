from __future__ import annotations
import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_llm_json(text: str, context: str = "") -> dict:
    """Robustly parse JSON from LLM output that may be wrapped in markdown fences.

    Handles all Gemini/OpenAI output variants:
      - Raw JSON:  {...}
      - Fenced:    ```json\n{...}\n```
      - Fenced:    ```\n{...}\n```

    Returns a dict (empty on failure).
    """
    text = text.strip()

    # 1. Try extracting JSON from inside markdown fences via regex (most reliable)
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass  # fall through to raw parse

    # 2. Try the raw text directly (LLM already returned clean JSON)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Last resort: find the outermost {...} block
    start = text.find("{")
    end   = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    tag = f" [{context}]" if context else ""
    logger.warning("parse_llm_json%s: all strategies failed. Raw snippet: %r", tag, text[:300])
    return {}