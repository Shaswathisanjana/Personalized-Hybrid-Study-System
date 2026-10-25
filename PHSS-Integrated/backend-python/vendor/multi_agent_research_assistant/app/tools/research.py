"""
Research tools for agents to interact with external data sources.
Implements web search, academic search, and citation extraction.
"""
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain_community.utilities import ArxivAPIWrapper
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class ResearchToolkit:
    """Collection of research tools with fallback mechanisms."""
    
    def __init__(self):
        self.tavily_available = bool(settings.TAVILY_API_KEY)
        
    def get_web_search_tool(self):
        """
        Returns configured web search tool (Tavily).
        """
        if self.tavily_available:
            try:
                return TavilySearch(
                    api_key=settings.TAVILY_API_KEY,
                    max_results=3,

                    search_depth="basic", # 
                    include_raw_content=False,
                    include_answer=True,
                    exclude_domains=["facebook.com", "instagram.com", "twitter.com", "youtube.com", "tiktok.com"]
                )
            except Exception:
                logger.info("Tavily search API key missing or invalid, using mock fallback.")
                return self._get_mock_search_tool()
        else:
            logger.warning("No web search API configured, using mock data")
            return self._get_mock_search_tool()

    def _get_mock_search_tool(self):
        """Fallback search tool that keeps workflow functional without external keys."""

        class _MockSearchTool:
            def invoke(self, query: str) -> List[Dict[str, Any]]:
                return [
                    {
                        "title": "Search API not configured",
                        "url": "",
                        "content": (
                            "Web search is currently running in fallback mode because no "
                            "TAVILY_API_KEY is configured. "
                            f"Original query: {query}"
                        ),
                        "score": 0.0,
                    }
                ]

        return _MockSearchTool()


@tool
def academic_search(query: str, max_results: int = 3) -> str:
    """
    Search academic databases (Arxiv) for peer-reviewed papers.
    
    Args:
        query: Scientific query string
        max_results: Maximum number of papers to return
        
    Returns:
        Formatted string with paper titles, abstracts, and URLs
    """
    try:
        arxiv = ArxivAPIWrapper(
            top_k_results=max_results,
            doc_content_chars_max=2000,
            load_max_docs=3,
            sort_by="relevance"
            # load_all_available_meta=True,
            # load_all_available_content=True,
        )
        results = arxiv.run(query)
        return results
    except Exception as e:
        logger.error(f"Academic search failed: {e}")
        return f"Academic search unavailable: {str(e)}"


@tool
def extract_citations(text: str) -> List[Dict[str, str]]:
    """
    Extract and format citations from research text.
    
    Args:
        text: Text containing inline citations
        
    Returns:
        List of citation dictionaries with title, url, accessed date
    """
    import re
    from datetime import datetime
    
    # Regex to find [Source: URL] patterns
    citation_pattern = r'\[(?:Source:\s*)?([^\]]+)\]'
    matches = re.findall(citation_pattern, text)
    
    citations = []
    for idx, match in enumerate(matches, 1):
        citations.append({
            "id": idx,
            "reference": match,
            "accessed": datetime.now().strftime("%Y-%m-%d")
        })
    
    return citations