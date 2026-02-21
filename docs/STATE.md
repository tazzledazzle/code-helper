# State: Index Status and Ingest Job Behavior

This document describes how the crew API tracks RAG index status and how ingest Job creation behaves (stable job names, concurrency, and refresh from Kubernetes).

## Index status values

The API exposes `index_status` on **GET /project**. Possible values:

| Value      | Meaning |
|-----------|--------|
| `idle`    | No project set or no Job exists for the current project. |
| `indexing`| An ingest Job for this project exists and is active (running). |
| `ready`   | The ingest Job has completed successfully (at least one succeeded completion). RAG is ready for this project. |
| `failed`  | The ingest Job has failed (at least one failed completion). |

**Is RAG ready?** Use **GET /project**. When `index_status` is `ready` or `failed`, the ingest Job has finished; `ready` means the index is usable.

## POST /project: concurrency and 409

- Each project has a **stable job name**: `ingest-<8-char-sha256(project_path)>`. There is at most one Job per project path.
- **POST /project** is **get-before-create**: it checks for an existing Job before creating.  
  - If no Job exists (404), it creates one and returns **200** with `{"status": "accepted", "job_id": "ingest-..."}`.  
  - If a Job exists and is **completed** (succeeded or failed), it returns the existing `job_id` (idempotent 200).  
  - If a Job exists and is **active** (still indexing), it **does not** create a second Job and returns **409** with:
    - `{"error": "already_indexing", "job_id": "ingest-..."}`  
  So concurrent or duplicate POSTs for the same project while indexing is in progress get 409 and the same `job_id`.

## GET /project: refresh from Kubernetes when indexing

- When `index_status` is **indexing** and `project_path` is set, **GET /project** refreshes status from the Kubernetes Job (poll-on-read). It calls the cluster to read the Job status and updates `index_status` to `ready`, `failed`, or keeps `indexing` as appropriate.
- When `index_status` is not `indexing` or `project_path` is unset, the response uses the in-memory state only (no K8s read).
- So clients can poll **GET /project** to see when indexing has completed (ready or failed) without a separate runbook implementation in this phase.

## In-memory state and restarts

- `project_path`, `pinned_repo`, and `index_status` are stored in **in-memory** `app.state`. After a process restart, that state is lost (e.g. back to idle/no project).
- If the caller still knows `project_path` and a Job exists in the cluster, they can **POST /project** again (idempotent if the Job completed, or 409 if it is still active). **GET /project** can still refresh from K8s when `index_status` is `indexing` and `project_path` is set; after a restart, without app state, GET will not refresh until project is set again via POST.
