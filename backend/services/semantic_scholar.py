"""
Thin client around the Semantic Scholar Graph API.
No API key required for low-volume use (a free key raises your rate limit —
see https://www.semanticscholar.org/product/api).
"""
import os
import httpx

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")  # optional


async def search_papers(query: str, limit: int = 8) -> list[dict]:
    """Return a list of paper dicts: title, authors, year, url, abstract."""
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,url,abstract,externalIds",
    }
    headers = {"x-api-key": API_KEY} if API_KEY else {}

    print("Semantic Scholar API Key:", API_KEY)
    print("Headers:", headers)

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(BASE_URL, params=params, headers=headers)
        if resp.status_code != 200:
            print("Status:", resp.status_code)
            print("Response headers:", dict(resp.headers))
            print("Response body:", resp.text)

        resp.raise_for_status()
        data = resp.json()

    papers = []
    for item in data.get("data", []):
        papers.append(
            {
                "title": item.get("title") or "Untitled",
                "authors": [a.get("name", "") for a in item.get("authors", [])],
                "year": item.get("year"),
                "url": item.get("url"),
                "abstract": item.get("abstract") or "",
            }
        )
    return papers
