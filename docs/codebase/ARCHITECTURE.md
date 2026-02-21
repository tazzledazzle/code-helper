# Architecture

**Analysis Date:** 2025-02-20

## Pattern Overview

**Overall:** Multi-service app with a central Crew API, a Runner service for safe command execution, an Ingest pipeline (CLI or K8s Job), and a minimal Chat UI. CrewAI provides a hierarchical multi-agent process (Manager + Researcher, Coder, Runner) that uses RAG, web search, and the Runner to answer user messages.

**Key Characteristics:**
- Crew API is the main HTTP entrypoint (project, chat, run, health); it calls Runner and K8s for ingest Jobs.
- Runner is a separate FastAPI app that validates project path (ALLOWED_ROOT) and command allowlist, then runs subprocess.
- Ingest runs as a one-shot process (directory → chunk → embed → Chroma upsert), either via `python -m ingest.run` or as a K8s Job.
- State is in-memory in crew_api (project_path, index_status); vector state is in Chroma; no shared DB for app state.

## Layers

**Crew API (HTTP + orchestration):**
- Purpose: Expose /health, /project, /chat, /run; create ingest Jobs; run crew kickoff.
- Location: `crew_api/`
- Contains: `app.py` (FastAPI app, routes), `chat.py` (handle_chat → create_crew, kickoff), `runner_client.py` (async execute), `ingest_job.py` (K8s Job creation), `crew/` (agents, tasks, crew, tools).
- Depends on: FastAPI, CrewAI, httpx, kubernetes, ingest.vector_store (via RAG tool).
- Used by: Chat UI, CLI, any HTTP client.

**Runner (command execution):**
- Purpose: Execute allowlisted commands in a project path under ALLOWED_ROOT.
- Location: `runner/`
- Contains: `app.py` (FastAPI app, POST /execute, path and command validation, subprocess.run).
- Depends on: FastAPI, pydantic, os/subprocess.
- Used by: crew_api (POST /run, RunnerTool in crew).

**Ingest (indexing pipeline):**
- Purpose: Walk project dir, chunk files, embed (Ollama or injectable), upsert to Chroma.
- Location: `ingest/`
- Contains: `run.py` (run_ingest, _main), `chunk.py`, `embed.py`, `vector_store.py`.
- Depends on: chromadb, httpx (embed).
- Used by: crew_api (indirectly via K8s Job); CLI entrypoint is `python -m ingest.run`.

**Crew (agents and tools):**
- Purpose: Define Manager, Researcher, Coder, Runner agents and tasks; provide RAG, Search, Runner, and stub tools.
- Location: `crew_api/crew/`
- Contains: `crew.py` (create_crew), `agents.py`, `tasks.py`, `tools/` (rag_tool, search_tool, runner_tool, stubs).
- Depends on: CrewAI, ingest.vector_store, crew_api.runner_client.
- Used by: crew_api.chat (handle_chat).

**CLI:**
- Purpose: Subcommands run-tests (POST /run) and chat (POST /chat or interactive).
- Location: `cli/`
- Contains: `main.py` (argparse, httpx to crew_api).
- Depends on: httpx.
- Used by: End users (entrypoint `code-helper` in pyproject.toml).

**Chat UI:**
- Purpose: Minimal browser client for POST /chat (and optional project_path).
- Location: `code-helper/chat_ui/`
- Contains: `index.html`, `app.js` (fetch to CODE_HELPER_API or ?api=), no build step.
- Depends on: Crew API base URL (env or query param).
- Used by: End users (serve via `python3 -m http.server 3000`).

## Data Flow

**Chat / run flow:**
1. User sends message (Chat UI or CLI) → crew_api POST /chat.
2. handle_chat builds inputs, create_crew() builds Crew (hierarchical), crew.kickoff(inputs) runs agents.
3. Researcher uses SearchTool (Tavily/Serper or stub); Coder uses RAGTool (Chroma) and StubCodeTool; Runner uses RunnerTool → runner_client.execute → Runner POST /execute.
4. Result (raw/final_output, sources) returned as JSON.

**Run-tests flow:**
1. CLI or client POST /run with project_path and action (e.g. run_tests).
2. crew_api calls runner_client.execute(project_path, command) toward RUNNER_URL.
3. Runner validates path under ALLOWED_ROOT and command allowlist, runs subprocess, returns exit_code, stdout, stderr, duration_seconds.
4. crew_api returns success, summary, stdout, stderr, duration_seconds.

**Ingest flow:**
1. Client POST /project with project_path → crew_api sets app state (index_status=indexing) and creates K8s Job via ingest_job.create (image, args=[project_path], env VECTOR_DB_URL).
2. Job pod runs `python -m ingest.run <project_path>`; run_ingest chunks dir, embeds (Ollama or injectable), upserts to Chroma collection derived from path.
3. No callback to crew_api when Job completes; index_status is not updated automatically (stays "indexing" unless changed elsewhere).

**State Management:**
- Crew API: in-memory app.state (project_path, pinned_repo, index_status); optional app.state overrides for runner_url, runner_transport, k8s_namespace, vector_db_url, ingest_image.
- Runner: stateless per request.
- Chroma: persistent (or ephemeral in tests) vector collections keyed by collection_id (e.g. code_<project_name>).

## Key Abstractions

**Runner client:**
- Purpose: Call Runner POST /execute with project_path, command, optional cwd, env, timeout.
- Examples: `crew_api/runner_client.py`
- Pattern: Async httpx; optional custom transport for tests (e.g. test_crew_api_run.py).

**Ingest pipeline:**
- Purpose: Single function run_ingest(project_path, collection_id, vector_db_url, client?, embed_func?) to chunk, embed, upsert.
- Examples: `ingest/run.py`
- Pattern: Injectable Chroma client and embed_func for tests; otherwise Chroma HTTP or in-memory, Ollama for embed.

**Crew tools:**
- Purpose: RAG (Chroma query), Search (Tavily/Serper/stub), Runner (execute_sync or runner_client), plus stubs for tests.
- Examples: `crew_api/crew/tools/rag_tool.py`, `search_tool.py`, `runner_tool.py`, `stubs.py`
- Pattern: CrewAI BaseTool with Pydantic args_schema; inject client/embedding_function or execute_sync for testing.

## Entry Points

**Crew API:**
- Location: `crew_api/app.py` (uvicorn crew_api.app:app).
- Triggers: HTTP requests to /health, /project, /chat, /run.
- Responsibilities: Health, project state, chat (crew kickoff), run (proxy to Runner), create ingest Job.

**Runner:**
- Location: `runner/app.py` (uvicorn runner.app:app).
- Triggers: HTTP POST /execute.
- Responsibilities: Validate project_path and command, run subprocess, return exit_code/stdout/stderr/duration.

**Ingest:**
- Location: `ingest/run.py` (_main when __name__ == "__main__").
- Triggers: CLI `python -m ingest.run <project_path>` or K8s Job args.
- Responsibilities: Chunk, embed, upsert to Chroma.

**CLI:**
- Location: `cli/main.py` (script code-helper in pyproject.toml).
- Triggers: `code-helper run-tests [--path]`, `code-helper chat [--path] [--message]`.
- Responsibilities: HTTP to crew_api for /run and /chat.

## Error Handling

**Strategy:** HTTP exceptions for invalid input; propagate client/network errors (e.g. httpx.raise_for_status); Runner returns 400 with body {"error": "...", "code": "invalid_input"} for path/command validation.

**Patterns:**
- Runner: _validate_project_path, _validate_command raise HTTPException 400 with detail dict; custom exception_handler in app returns JSON with "code": "invalid_input".
- crew_api: No global exception handler mapped; FastAPI default for unhandled.
- Ingest: NotADirectoryError, ValueError from embed; sys.exit(1) in _main on usage/path errors.

## Cross-Cutting Concerns

**Logging:** Default FastAPI/uvicorn; no structured logging or correlation IDs.

**Validation:** Pydantic models for request bodies (ProjectPostBody, ChatPostBody, RunPostBody, ExecuteRequest); Runner validates path (realpath under ALLOWED_ROOT) and command prefix allowlist.

**Authentication:** None; all endpoints are unauthenticated.

---

*Architecture analysis: 2025-02-20*
