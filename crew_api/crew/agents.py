"""Crew agents: Manager (orchestrator), Researcher, Coder, Runner."""

from typing import Any

from crewai import Agent

from crew_api.crew.tools import RAGTool, RunnerTool, SearchTool, StubCodeTool, StubRunTool, StubSearchTool


def create_manager(llm: Any = None) -> Agent:
    """Orchestrator agent; delegates to Researcher, Coder, Runner."""
    return Agent(
        role="Manager",
        goal="Coordinate the team: assign research, code, and run tasks and validate outputs.",
        backstory="You are an experienced technical lead who delegates work and ensures quality.",
        llm=llm,
        allow_delegation=True,
    )


def create_researcher(llm: Any = None) -> Agent:
    """Researcher agent; uses web search tool (Tavily/Serper or stub)."""
    return Agent(
        role="Researcher",
        goal="Find and summarize relevant information (web search).",
        backstory="You are a thorough researcher who gathers facts before recommendations.",
        llm=llm,
        tools=[SearchTool()],
    )


def create_coder(llm: Any = None) -> Agent:
    """Coder agent; uses RAG and stub code suggestion tools."""
    return Agent(
        role="Coder",
        goal="Explain or suggest code changes and implementations.",
        backstory="You are a senior developer who writes clear, correct code.",
        llm=llm,
        tools=[RAGTool(), StubCodeTool()],
    )


def create_runner(llm: Any = None, runner_url: str | None = None) -> Agent:
    """Runner agent; uses RunnerTool to execute commands via runner client."""
    return Agent(
        role="Runner",
        goal="Run tests and report results.",
        backstory="You are a QA engineer who runs tests and reports pass/fail.",
        llm=llm,
        tools=[RunnerTool(runner_url=runner_url)],
    )
