"""Crew definition: hierarchical process with Manager and three agents."""

from typing import Any

from crewai import Crew
from crewai.process import Process

from crew_api.crew.agents import (
    create_manager,
    create_researcher,
    create_coder,
    create_runner,
)
from crew_api.crew.tasks import (
    create_research_task,
    create_code_task,
    create_run_task,
)


def create_crew(
    llm: Any = None,
    manager_llm: Any = None,
) -> Crew:
    """Build a Crew with Manager (orchestrator), Researcher, Coder, Runner.

    Uses hierarchical process. LLMs default to env (OPENAI_BASE_URL / Ollama)
    when None. Pass stub LLMs in tests to avoid network.
    """
    manager = create_manager(llm=manager_llm)
    researcher = create_researcher(llm=llm)
    coder = create_coder(llm=llm)
    runner = create_runner(llm=llm)

    agents = [researcher, coder, runner]

    research_task = create_research_task(researcher)
    code_task = create_code_task(coder, context=[research_task])
    run_task = create_run_task(runner, context=[research_task, code_task])
    tasks = [research_task, code_task, run_task]

    return Crew(
        agents=agents,
        tasks=tasks,
        process=Process.hierarchical,
        manager_llm=manager_llm,
        manager_agent=manager,
        memory=False,
    )
