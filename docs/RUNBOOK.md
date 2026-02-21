# Code Helper — Runbook

How to run, operate, and troubleshoot Code Helper. For environment variables and timeouts see [CONFIG.md](CONFIG.md). For index status and ingest Job behavior see [STATE.md](STATE.md). For per-failure runbooks, healthy vs broken state, and operational assumptions see [FAILURE-MODES.md](FAILURE-MODES.md).

---

## Run

### Dependency order

Crew API depends on **Runner** and **Chroma** (and optionally an LLM). Start them first; then start Crew API.

### Docker Compose

From `code-helper/`:

```bash
# Start all (crew_api, runner, chroma)
docker compose up -d

# Stop
docker compose down
```

Ports: Crew API 8000, Runner 8080, Chroma 8001→8000. Optional Ollama is commented out in `docker-compose.yml`; uncomment if you need local embeddings/LLM.

**Key env (see [CONFIG.md](CONFIG.md) for full contract):** `RUNNER_URL`, `VECTOR_DB_URL`, `LLM_URL` for Crew API; `ALLOWED_ROOT` for Runner. Compose sets defaults (e.g. `RUNNER_URL=http://runner:8080`, `VECTOR_DB_URL=http://chroma:8000`).

### Kubernetes

From repo root (e.g. kind/minikube):

```bash
# Apply all manifests (namespace, configmap, deployments, services)
kubectl apply -f code-helper/k8s/

# Load local images (kind)
kind load docker-image code-helper-crew code-helper-runner code-helper-ingest --name <cluster-name>
docker pull chromadb/chroma:latest
kind load docker-image chromadb/chroma:latest --name <cluster-name>

# Access Crew API (no Ingress)
kubectl port-forward -n code-helper svc/crew-api 8000:8000
curl http://localhost:8000/health   # expect {"status":"ok"}
```

Stop: delete namespace `code-helper` or scale deployments to 0. Full apply order and port-forward options: [k8s/README.md](../k8s/README.md).

### Graceful shutdown

Crew API and Runner are run with uvicorn’s **graceful shutdown** enabled. On **SIGTERM** (e.g. `docker compose down`, `kubectl delete pod`, or scale to 0):

- The process **stops accepting new connections** and waits for in-flight requests to complete, up to a **bounded timeout**, then exits.
- **Crew API:** timeout **30 seconds**. In-flight /chat or /run requests that finish within 30s complete normally; after 30s the process exits and any remaining requests are terminated.
- **Runner:** timeout **60 seconds**. In-flight POST /execute (command runs) that finish within 60s complete; long-running commands may be cut off after 60s.

So you can stop the system without abandoning in-flight work as long as requests finish within these bounds; otherwise the drain is bounded and the process exits. The Crew API logs `graceful_shutdown` when the lifespan shutdown phase runs.

---

## Operate

### Set project and index

1. **POST /project** with `{"project_path": "/workspace/my-project"}` (path must be under Runner’s `ALLOWED_ROOT`).
2. API creates an ingest Job and returns `job_id`. Index status is then `indexing`.
3. **Poll GET /project** until `index_status` is `ready` or `failed`. When `ready`, RAG is available for that project. See [STATE.md](STATE.md) for 409 when already indexing and stable job names.

### Chat

**POST /chat** with `project_path` and `message`. Use the same `project_path` you set above so RAG and tools target the right repo.

### Run tests

**POST /run** with `project_path` and action (e.g. run_tests), or use the CLI: `code-helper run-tests` (points at Crew API). Runner executes allowlisted commands under `ALLOWED_ROOT`.

---

## Troubleshoot

### Readiness fails (GET /readyz returns 503)

- Crew API readiness checks Runner, Chroma, and (if configured) LLM. Check URLs: `RUNNER_URL`, `VECTOR_DB_URL`, `LLM_URL` (see [CONFIG.md](CONFIG.md)).
- With `CREW_API_VALIDATE_DEPS=1`, startup fails if those are unreachable; otherwise readiness stays 503 until they are up.
- Verify Runner: `curl http://<runner>/health`. Verify Chroma is reachable from Crew API (network/DNS).

### Crew API 5xx or timeouts

- Check logs (structured; include `request_id` for correlation).
- Ensure Runner and Chroma are reachable from the Crew API pod/container. Check timeouts in [CONFIG.md](CONFIG.md) (e.g. Runner 60s, readiness 5s).
- **GET /metrics** (Crew API and Runner) for request count and latency by route.

### Index stuck or “already indexing” (409)

- **GET /project** refreshes index status from the Kubernetes Job when status is `indexing`; poll until `ready` or `failed`. If it stays `indexing`, check the Job in the cluster: `kubectl get jobs -n code-helper`, `kubectl logs -n code-helper job/<job_id> -f`. See [STATE.md](STATE.md) for job naming and 409 behavior.
- On 409, another request already started indexing that project; wait or use the returned `job_id` to watch the same Job.

### Chroma down or empty index

- Restart Chroma (Compose: `docker compose restart chroma`; K8s: restart the Chroma deployment). Data is in Chroma’s volume; if the volume was lost, re-index via POST /project and wait for `ready`.

### Escalation

- Use **request_id** in logs to trace a single chat or run.
- Use **GET /metrics** on Crew API and Runner for rates and latency.
- For ingest: inspect the K8s Job and pod logs; confirm `VECTOR_DB_URL` and project path are correct.

---

## Failure modes & assumptions

For **per-failure runbooks** (Crew API 5xx, Runner timeouts, Chroma down, Ingest stuck) with when to use, steps, verification, and escalation, see **[FAILURE-MODES.md](FAILURE-MODES.md)**.

That document also covers **healthy vs broken state** for Crew API, Runner, Chroma, and Ingest, and **operational assumptions**: single-replica design, in-memory state (lost on restart; see [STATE.md](STATE.md)), and how to **disable** (stop services) or **rollback** (redeploy previous image; re-index if Chroma data was lost).
