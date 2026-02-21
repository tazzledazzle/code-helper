# Technology Stack

**Analysis Date:** 2025-02-20

## Languages

**Primary:**
- Python 3.12–3.14 (required by `code-helper/pyproject.toml`); project uses 3.13 (`.python-version`: 3.13) for development and Docker images.

**Secondary:**
- JavaScript (vanilla) in `code-helper/chat_ui/` (app.js, index.html) for the minimal chat client; no framework or build step.

## Runtime

**Environment:**
- CPython 3.13 (slim base in Docker: `python:3.13-slim`).

**Package Manager:**
- pip + setuptools; optional lockfile via uv (`code-helper/uv.lock` present).
- Install: `pip install -e .` (editable install from repo root).

## Frameworks

**Core:**
- FastAPI (>=0.115) – crew_api (`crew_api/app.py`) and runner (`runner/app.py`) HTTP APIs.
- CrewAI (>=0.80) – hierarchical multi-agent crew (Manager, Researcher, Coder, Runner) in `crew_api/crew/`.
- Uvicorn (>=0.32) – ASGI server for both APIs.

**Testing:**
- pytest with pytest-asyncio (asyncio_mode: auto in `pyproject.toml`) for unit and API tests.

**Build/Dev:**
- setuptools (build-backend in `pyproject.toml`). No separate bundler for chat_ui.

## Key Dependencies

**Critical:**
- `crewai>=0.80` – agent/task/crew definitions and tools.
- `chromadb>=0.5` – vector store for RAG (ingest and RAG tool).
- `fastapi`, `uvicorn[standard]` – API layer.
- `httpx>=0.27` – sync/async HTTP client (CLI, runner_client, embed, search tools).
- `pydantic>=2`, `pydantic-settings>=2` – request/response and settings.
- `kubernetes>=31` – creating ingest Jobs from crew_api.

**Infrastructure:**
- Chroma (container: `chromadb/chroma:latest` in docker-compose).
- Optional: Ollama (commented in docker-compose) for embeddings and LLM.

## Configuration

**Environment:**
- No pydantic-settings module found; configuration is via `os.environ.get()` in app code (e.g. `crew_api/app.py`, `runner/app.py`, `ingest/run.py`, `crew_api/runner_client.py`).
- Key env vars: `RUNNER_URL`, `VECTOR_DB_URL`/`CHROMA_URL`, `ALLOWED_ROOT`, `K8S_NAMESPACE`, `INGEST_IMAGE`, `CREWAI_STORAGE_DIR`, `CODE_HELPER_API_URL`, `TAVILY_API_KEY`, `SERPER_API_KEY`, `LLM_URL` (referenced in k8s ConfigMap).

**Build:**
- `code-helper/pyproject.toml` – project definition, scripts (`code-helper = "cli.main:main"`), setuptools package find (runner, ingest, crew_api, cli), pytest options (asyncio_mode, testpaths, pythonpath).

## Platform Requirements

**Development:**
- Python 3.12–3.14; recommended 3.13. Optional: Ollama for local embeddings/LLM; Tavily or Serper API keys for live web search.

**Production:**
- Deployable via Docker (Dockerfile.crew_api, Dockerfile.runner, Dockerfile.ingest) and Kubernetes manifests in `code-helper/k8s/` (namespace, configmap, deployments for crew-api, runner, vector-db, ingest Job template, services, ingress).

---

*Stack analysis: 2025-02-20*
