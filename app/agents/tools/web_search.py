"""Web search tool — DuckDuckGo (free) with optional Tavily upgrade."""

from langchain_core.tools import tool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@tool
def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web for information about a topic.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        List of dicts with keys: title, url, snippet.
    """
    max_results = min(max_results, settings.max_research_results)

    if settings.use_tavily:
        return _tavily_search(query, max_results)
    return _duckduckgo_search(query, max_results)


def _duckduckgo_search(query: str, max_results: int) -> list[dict]:
    try:
        from duckduckgo_search import DDGS  # noqa: PLC0415

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                    }
                )
        logger.debug("web_search_ddg", query=query[:60], results=len(results))
        return results
    except Exception as exc:
        logger.warning("web_search_failed", query=query[:60], error=str(exc))
        return []


def _tavily_search(query: str, max_results: int) -> list[dict]:
    try:
        from tavily import TavilyClient  # noqa: PLC0415

        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query, max_results=max_results)
        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]
        logger.debug("web_search_tavily", query=query[:60], results=len(results))
        return results
    except Exception as exc:
        logger.warning("tavily_search_failed", error=str(exc))
        return _duckduckgo_search(query, max_results)
