"""Web search tool: Tavily or Serper when API key is set, else stub."""

import os
from typing import Optional

import httpx
from crewai.tools.base_tool import BaseTool
from pydantic import BaseModel, Field

STUB_MESSAGE = "Search result (no API key configured). Use TAVILY_API_KEY or SERPER_API_KEY for live search."


class SearchToolInput(BaseModel):
    """Input schema for SearchTool."""

    query: str = Field(..., description="Search query.")


def _search_tavily(query: str, api_key: str) -> str:
    """Call Tavily search API; return formatted results or error string."""
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": 5},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Tavily search failed: {e}"
    results = data.get("results") or []
    if not results:
        return data.get("answer") or "No results found."
    lines = [f"- {hit.get('title', '')}: {hit.get('url', '')}\n  {hit.get('content', '')}" for hit in results]
    return "\n".join(lines)


def _search_serper(query: str, api_key: str) -> str:
    """Call Serper search API; return formatted results or error string."""
    try:
        with httpx.Client(timeout=30.0) as client:
            r = client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key},
                json={"q": query},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Serper search failed: {e}"
    organic = data.get("organic") or []
    if not organic:
        return "No results found."
    lines = [f"- {hit.get('title', '')}: {hit.get('link', '')}\n  {hit.get('snippet', '')}" for hit in organic[:5]]
    return "\n".join(lines)


class SearchTool(BaseTool):
    """Web search via Tavily or Serper when API key is set; otherwise returns stub message."""

    name: str = "web_search"
    description: str = (
        "Search the web for current information. Provide a query string. "
        "Returns search results or a stub message if no API key is configured."
    )
    args_schema: type[BaseModel] = SearchToolInput

    def _run(self, query: str) -> str:
        tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
        if tavily_key:
            return _search_tavily(query, tavily_key)
        serper_key = os.environ.get("SERPER_API_KEY", "").strip()
        if serper_key:
            return _search_serper(query, serper_key)
        return STUB_MESSAGE
