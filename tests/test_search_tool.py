"""Tests for SearchTool: web search (Tavily/Serper or stub)."""

import pytest

from crew_api.crew.tools import SearchTool


def test_search_tool_returns_search_or_stub_result():
    """Search tool: call with query returns string containing 'search' or stub message."""
    tool = SearchTool()
    result = tool.run(query="latest Python")
    assert result is not None
    assert isinstance(result, str)
    assert "search" in result.lower() or "stub" in result.lower() or "python" in result.lower()
