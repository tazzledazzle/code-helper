"""Tests for CrewAI crew (Manager + Researcher, Coder, Runner) and kickoff."""

import os
import tempfile

import pytest
from crewai.llms.base_llm import BaseLLM
from crewai.crews.crew_output import CrewOutput

from crew_api.crew import create_crew


class _StubLLM(BaseLLM):
    """Minimal LLM that returns a fixed string (no network). Used for tests."""

    def __init__(self) -> None:
        super().__init__(model="stub")

    def call(
        self,
        messages,
        tools=None,
        callbacks=None,
        available_functions=None,
        from_task=None,
        from_agent=None,
        response_model=None,
    ):
        return "Task completed."

    async def acall(
        self,
        messages,
        tools=None,
        callbacks=None,
        available_functions=None,
        from_task=None,
        from_agent=None,
        response_model=None,
    ):
        return "Task completed."


def test_crew_kickoff_returns_result_with_expected_structure():
    """Build crew with Manager, Researcher, Coder, Runner; kickoff and assert result shape."""
    with tempfile.TemporaryDirectory() as tmp:
        prev = os.environ.get("CREWAI_STORAGE_DIR")
        os.environ["CREWAI_STORAGE_DIR"] = tmp
        try:
            stub_llm = _StubLLM()
            crew = create_crew(llm=stub_llm, manager_llm=stub_llm)
            result = crew.kickoff(inputs={"message": "hello"})
            assert result is not None
            assert isinstance(result, CrewOutput)
            assert hasattr(result, "raw")
            assert isinstance(result.raw, str)
            assert hasattr(result, "tasks_output")
        finally:
            if prev is None:
                os.environ.pop("CREWAI_STORAGE_DIR", None)
            else:
                os.environ["CREWAI_STORAGE_DIR"] = prev
