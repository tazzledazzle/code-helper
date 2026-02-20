"""Runner tool: execute command via runner client (sync wrapper or injected callback)."""

import asyncio
from typing import Callable, Optional

from crewai.tools.base_tool import BaseTool
from pydantic import BaseModel, Field

from crew_api import runner_client


class RunnerToolInput(BaseModel):
    """Input schema for RunnerTool."""

    project_path: str = Field(..., description="Project directory path.")
    command: list[str] = Field(..., description="Command and args, e.g. ['pytest'].")


def _default_execute_sync(project_path: str, command: list[str], runner_url: Optional[str] = None) -> dict:
    """Run async runner_client.execute in a sync context."""
    return asyncio.run(
        runner_client.execute(project_path=project_path, command=command, runner_url=runner_url)
    )


def _run_summary(result: dict) -> str:
    """Build a short summary from execute result."""
    exit_code = result.get("exit_code", -1)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    duration = result.get("duration_seconds", 0)
    if exit_code == 0:
        return f"Exit code: 0. {stdout.strip() or 'Tests passed.'} (duration: {duration}s)"
    return f"Exit code: {exit_code}. stderr: {stderr.strip() or stdout.strip() or 'No output'} (duration: {duration}s)"


class RunnerTool(BaseTool):
    """Run a command in the project via the Runner service; accepts optional execute_sync for tests."""

    name: str = "run_command"
    description: str = (
        "Run a command (e.g. pytest) in the given project path. "
        "Returns exit code and summary from the Runner service."
    )
    args_schema: type[BaseModel] = RunnerToolInput

    execute_sync: Optional[Callable[[str, list[str]], dict]] = None
    runner_url: Optional[str] = None

    def _run(self, project_path: str, command: list[str]) -> str:
        if self.execute_sync is not None:
            result = self.execute_sync(project_path, command)
        else:
            result = _default_execute_sync(project_path, command, runner_url=self.runner_url)
        return _run_summary(result)
