"""Tests for RunnerTool: execute command via runner client (or injected callback)."""

import pytest

from crew_api.crew.tools import RunnerTool


def test_runner_tool_returns_exit_code_and_summary():
    """Runner tool: with injected sync callback, returns result containing exit_code or passed."""
    def fake_execute_sync(project_path: str, command: list[str]):
        return {
            "exit_code": 0,
            "stdout": "ok",
            "stderr": "",
            "duration_seconds": 1,
        }

    tool = RunnerTool(execute_sync=fake_execute_sync)
    result = tool.run(project_path="/tmp", command=["pytest"])
    assert result is not None
    assert isinstance(result, str)
    assert "0" in result or "passed" in result or "ok" in result
