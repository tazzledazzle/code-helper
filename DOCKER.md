# Docker images and compose

## Images

- **Dockerfile.crew_api** — Crew API (FastAPI), port 8000
- **Dockerfile.runner** — Runner service (POST /execute), port 8080
- **Dockerfile.ingest** — Ingest job (`python -m ingest.run <project_path>`), for K8s Job or one-off runs

All use `python:3.13-slim`, copy the repo, and `pip install -e .`.

## Build

```bash
# From repo root (code-helper/)
docker build -f Dockerfile.crew_api -t code-helper-crew .
docker build -f Dockerfile.runner   -t code-helper-runner .
docker build -f Dockerfile.ingest   -t code-helper-ingest .
```

## docker-compose

Starts crew_api, runner, chroma; optional ollama (commented out).

```bash
docker compose up -d
# Or only API + runner + chroma (no ollama):
docker compose up -d crew_api runner chroma
```

Env:

- **crew_api**: `RUNNER_URL=http://runner:8080`, `VECTOR_DB_URL` / `CHROMA_URL=http://chroma:8000`
- **runner**: `ALLOWED_ROOT=/workspace`
- **ingest** (when run via Job): pass `project_path` as container args; set `VECTOR_DB_URL` or `CHROMA_URL`

Ports: crew_api 8000, runner 8080, chroma 8001→8000.

## Smoke test

With stack running (`docker compose up -d` or the two containers run manually):

1. **Crew API health**
   ```bash
   curl http://localhost:8000/health
   # Expect: {"status":"ok"}
   ```

2. **Runner execute**
   ```bash
   curl -s -X POST http://localhost:8080/execute \
     -H "Content-Type: application/json" \
     -d '{"project_path":"/workspace","command":["python","-c","print(42)"]}'
   ```
   Expect JSON with `exit_code`, `stdout`, `stderr`, `duration_seconds`. Use a path under `ALLOWED_ROOT` (e.g. `/workspace` with compose volume).

If running runner alone (no compose), set `ALLOWED_ROOT` and use a path under it, e.g.:

```bash
docker run --rm -e ALLOWED_ROOT=/tmp -p 8080:8080 code-helper-runner
# In another terminal:
curl -s -X POST http://localhost:8080/execute \
  -H "Content-Type: application/json" \
  -d '{"project_path":"/tmp","command":["python","-c","print(1)"]}'
```

## Ingest (K8s Job example)

Override CMD with project path; set vector DB URL via env:

```yaml
args: ["/workspace/my-project"]
env:
  - name: VECTOR_DB_URL
    value: "http://chroma:8000"
```
