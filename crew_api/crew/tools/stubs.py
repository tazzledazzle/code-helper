"""Stub tools for crew agents (no external services)."""

from crewai.tools.base_tool import BaseTool


class StubSearchTool(BaseTool):
    """Stub web search tool; returns a fixed string."""

    name: str = "stub_search"
    description: str = "Search the web (stub). Returns a fixed search result."

    def _run(self) -> str:
        return "search result"


class StubCodeTool(BaseTool):
    """Stub code suggestion tool; returns a fixed string."""

    name: str = "stub_code"
    description: str = "Suggest or explain code (stub). Returns a fixed suggestion."

    def _run(self) -> str:
        return "code suggestion"


class StubRunTool(BaseTool):
    """Stub test runner tool; returns a fixed string."""

    name: str = "stub_run"
    description: str = "Run tests (stub). Returns a fixed result."

    def _run(self) -> str:
        return "tests passed"
