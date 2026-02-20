"""Crew tasks: research, code, run (assigned to Researcher, Coder, Runner)."""

from crewai import Agent, Task


def create_research_task(researcher: Agent) -> Task:
    """Task: research using the user message."""
    return Task(
        description="Research the topic or question: {message}. Use your search tool and summarize findings.",
        expected_output="A short summary of research results.",
        agent=researcher,
    )


def create_code_task(coder: Agent, context: list[Task] | None = None) -> Task:
    """Task: suggest or explain code related to the request."""
    return Task(
        description="Based on the request '{message}', suggest or explain relevant code.",
        expected_output="A clear code suggestion or explanation.",
        agent=coder,
        context=context or [],
    )


def create_run_task(runner: Agent, context: list[Task] | None = None) -> Task:
    """Task: run tests and report results."""
    return Task(
        description="Run tests (using your run tool) and report whether they passed.",
        expected_output="Test result summary: passed or failed.",
        agent=runner,
        context=context or [],
    )
