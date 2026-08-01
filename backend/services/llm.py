"""
LLM wrapper using Google's Gemini API (free tier) — no local model, no GPU/RAM
overhead, no Anthropic dependency.

Requires a free API key from Google AI Studio (https://aistudio.google.com/apikey,
no credit card needed). Set it as an environment variable:

    export GEMINI_API_KEY=...

Uses the current `google-genai` SDK (the old `google-generativeai` package is
deprecated). Default model is gemini-2.5-flash, which has a generous free-tier
quota and is strong enough for summarization. If you hit rate limits, switch
MODEL to "gemini-2.5-flash-lite" for higher throughput at slightly lower quality.
"""
import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv()

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


MODEL ="models/gemini-3.6-flash"

print("GEMINI_API_KEY:", os.environ.get("GEMINI_API_KEY"))
print("MODEL:", MODEL)

def _generate_sync(prompt: str, max_output_tokens: int) -> str:
    """Blocking call to the Gemini API."""
    print("Using Gemini model:", MODEL)
    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config={"max_output_tokens": max_output_tokens},
    )
    return (response.text or "").strip()


async def _generate(prompt: str, max_output_tokens: int = 400) -> str:
    """Run the blocking SDK call in a thread so FastAPI stays async-friendly."""
    return await asyncio.to_thread(_generate_sync, prompt, max_output_tokens)


async def summarize_paper(title: str, abstract: str) -> str:
    if not abstract:
        return "No abstract available for this paper."

    prompt = (
        "Summarize the following paper abstract in 2-3 sentences for a "
        "student doing a literature review. Focus on: what problem it "
        "solves, the method, and the key result. Respond with only the "
        "summary, no preamble.\n\n"
        f"Title: {title}\n\nAbstract: {abstract}"
    )
    return await _generate(prompt, max_output_tokens=300)


async def build_comparison_table(topic: str, paper_summaries: list[dict]) -> str:
    """Ask Gemini to produce a short markdown comparison table across papers."""
    joined = "\n\n".join(
        f"- {p['title']} ({p.get('year', 'n/a')}): {p['summary']}"
        for p in paper_summaries
    )
    prompt = (
        f"Topic: {topic}\n\n"
        f"Here are summarized papers:\n{joined}\n\n"
        "Produce a compact markdown table comparing these papers by "
        "Approach, Key Contribution, and Limitation. Keep cells short "
        "(under 12 words each). Respond with only the markdown table, "
        "no preamble or explanation."
    )
    return await _generate(prompt, max_output_tokens=700)
