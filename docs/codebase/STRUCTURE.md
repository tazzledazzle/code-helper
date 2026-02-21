# Codebase Structure

**Analysis Date:** 2025-02-20

## Directory Layout

```
code-helper/
├── crew_api/           # FastAPI app + crew (agents, tasks, tools)
│   ├── crew/
│   │   ├── tools/      # RAG, Search, Runner, stubs
│   │   ├── agents.py
│   │   ├── tasks.py
│   │   └── crew.py
│   ├── app.py
│   ├── chat.py
│   ├── runner_client.py
│   └── ingest_job.py
├── runner/             # FastAPI app for POST /execute
│   └── app.py
├── ingest/             # Chunk, embed, vector store
│   ├── run.py
│   ├── chunk.py
│   ├── embed.py
│   └── vector_store.py
├── cli/                # code-helper CLI (run-tests, chat)
│   └── main.py
├── chat_ui/            # Static HTML/JS chat client
│   ├── index.html
│   ├── app.js
│   └── README.md
├── k8s/                # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── services.yaml
│   ├── crew-api-deployment.yaml
│   ├── runner-deployment.yaml
│   ├── vector-db-deployment.yaml
│   ├── ingest-job.yaml
│   └── ingress.yaml
├── tests/              # Pytest tests
├── Dockerfile.crew_api
├── Dockerfile.runner
├── Dockerfile.ingest
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── .python-version
```

Repo root (pelotech) also contains:
- `docs/` (e.g. `docs/plans/`, `docs/COREWEAVE_HERD_PROJECT_BRAINSTORM.md`)
- `BYOP_PREP.md`, `RUN_INTERVIEW.md`
- Other projects: `block-tor-exit-nodes/`, `trace-dependency-map/` (separate pyproject.toml each).

## Directory Purposes

**crew_api:**
- Purpose: Main API and CrewAI crew definition.
- Contains: FastAPI app, routes, chat handler, runner client, K8s ingest Job creation, crew agents/tasks/tools.
- Key files: `crew_api/app.py`, `crew_api/chat.py`, `crew_api/runner_client.py`, `crew_api/ingest_job.py`, `crew_api/crew/crew.py`, `crew_api/crew/agents.py`, `crew_api/crew/tasks.py`, `crew_api/crew/tools/*.py`.

**runner:**
- Purpose: Isolated service to run allowlisted commands under ALLOWED_ROOT.
- Contains: Single FastAPI app with POST /execute and validation helpers.
- Key files: `runner/app.py`.

**ingest:**
- Purpose: Index a project directory into Chroma (chunk → embed → upsert).
- Contains: Chunking, Ollama-style embed client, Chroma upsert/query, run_ingest entrypoint.
- Key files: `ingest/run.py`, `ingest/chunk.py`, `ingest/embed.py`, `ingest/vector_store.py`.

**cli:**
- Purpose: User-facing CLI for run-tests and chat.
- Contains: argparse, httpx calls to crew_api.
- Key files: `cli/main.py`.

**chat_ui:**
- Purpose: Minimal browser UI for POST /chat.
- Contains: Static HTML/JS; no package.json or build.
- Key files: `chat_ui/index.html`, `chat_ui/app.js`.

**k8s:**
- Purpose: Deployments, services, ConfigMap, namespace, ingest Job template for code-helper stack.
- Key files: All `.yaml` under `k8s/`.

**tests:**
- Purpose: Pytest tests for runner, crew_api routes, crew kickoff, ingest, tools.
- Key files: `tests/test_*.py` (test_runner, test_crew_api_*, test_crew_crew, test_ingest_*, test_rag_tool, test_runner_tool, test_search_tool).

## Key File Locations

**Entry Points:**
- `crew_api/app.py`: Crew API FastAPI app (uvicorn).
- `runner/app.py`: Runner FastAPI app (uvicorn).
- `ingest/run.py`: Ingest CLI entry (`python -m ingest.run`); _main().
- `cli/main.py`: CLI entry (code-helper script).

**Configuration:**
- `pyproject.toml`: Package deps, scripts, pytest options.
- `k8s/configmap.yaml`: Env for crew-api and runner (e.g. RUNNER_URL, VECTOR_DB_URL, ALLOWED_ROOT).
- `.python-version`: 3.13.

**Core Logic:**
- Crew: `crew_api/crew/crew.py`, `agents.py`, `tasks.py`; tools in `crew_api/crew/tools/`.
- Runner validation and execute: `runner/app.py`.
- Ingest pipeline: `ingest/run.py`, `ingest/chunk.py`, `ingest/embed.py`, `ingest/vector_store.py`.
- Runner client: `crew_api/runner_client.py`; Job creation: `crew_api/ingest_job.py`.

**Testing:**
- All under `tests/`; pytest discovers `test_*.py`; asyncio tests use pytest-asyncio and httpx ASGITransport.

## Naming Conventions

**Files:**
- Python modules: lowercase with underscores (e.g. `runner_client.py`, `ingest_job.py`).
- Docker: `Dockerfile.<service>` (Dockerfile.crew_api, Dockerfile.runner, Dockerfile.ingest).
- K8s: kebab-case in metadata (crew-api, code-helper-ingest); filenames like `crew-api-deployment.yaml`.

**Directories:**
- Package names match top-level dirs: `crew_api`, `runner`, `ingest`, `cli` (in setuptools find).

## Where to Add New Code

**New API route (crew_api):**
- Add route in `crew_api/app.py`; shared logic in a new module under `crew_api/` if needed.

**New crew agent or task:**
- Agent: `crew_api/crew/agents.py` (and wire in `crew_api/crew/crew.py`).
- Task: `crew_api/crew/tasks.py` (and add to tasks list in crew.py).
- New tool: `crew_api/crew/tools/<name>_tool.py`, export in `crew_api/crew/tools/__init__.py`, assign in agents.py.

**New ingest step or store:**
- Pipeline: extend `ingest/run.py` or add module under `ingest/`.
- Vector/embed: `ingest/vector_store.py`, `ingest/embed.py`.

**New Runner validation:**
- `runner/app.py`: extend ALLOWED_COMMAND_PREFIXES or _validate_*.

**New test:**
- Co-located under `tests/`; name `test_<module>_<behavior>.py` or `test_<component>_<behavior>.py` (e.g. test_crew_api_chat.py, test_ingest_chunk.py).

**Utilities:**
- Shared helpers: add under `crew_api/`, `ingest/`, or `runner/` as appropriate, or a small `common/` if cross-cutting (none present today).

## Special Directories

**.venv:**
- Purpose: Virtual environment.
- Generated: Yes (uv/pip).
- Committed: No (typically in .gitignore).

**code_helper.egg-info:**
- Purpose: Setuptools build metadata.
- Generated: Yes.
- Committed: No.

**.pytest_cache:**
- Purpose: Pytest cache.
- Generated: Yes.
- Committed: No.

**chat_ui:**
- Purpose: Static assets only; no npm/Node project.
- Generated: No.
- Committed: Yes.

---

*Structure analysis: 2025-02-20*
