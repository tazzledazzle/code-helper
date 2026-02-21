"""Create Kubernetes Jobs for code-helper ingest."""

import hashlib

from kubernetes.client import BatchV1Api, V1Job, V1JobSpec, V1PodTemplateSpec, V1PodSpec, V1Container, V1ObjectMeta, V1EnvVar
from kubernetes.client.rest import ApiException


class IngestJobAlreadyActive(Exception):
    """Raised when an ingest Job for this project_path is already running (active)."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Ingest Job already active: {job_id}")


def _job_name(project_path: str) -> str:
    """Stable Job name per project_path (no timestamp): ingest-<8-char-hash>. DNS-1123 ≤63 chars."""
    h = hashlib.sha256(project_path.encode()).hexdigest()[:8]
    return f"ingest-{h}"


def get_job_index_status(project_path: str, namespace: str) -> str:
    """Return index status from Kubernetes Job: ready | failed | indexing | idle."""
    job_name = _job_name(project_path)
    api = BatchV1Api()
    try:
        job = api.read_namespaced_job(name=job_name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            return "idle"
        raise
    status = job.status
    if status is None:
        return "indexing"
    if (status.succeeded or 0) >= 1:
        return "ready"
    if (status.failed or 0) >= 1:
        return "failed"
    if (status.active or 0) > 0:
        return "indexing"
    return "indexing"


def create(
    project_path: str,
    namespace: str,
    vector_db_url: str,
    image: str = "code-helper-ingest",
) -> str:
    """Create an ingest Job in the given namespace, or return existing job name if completed. Raises IngestJobAlreadyActive if Job is already running."""
    job_name = _job_name(project_path)
    api = BatchV1Api()

    try:
        job = api.read_namespaced_job(name=job_name, namespace=namespace)
    except ApiException as e:
        if e.status == 404:
            # Job does not exist; create it
            pass
        else:
            raise
    else:
        status = job.status
        if status is not None and (status.active or 0) > 0:
            raise IngestJobAlreadyActive(job_name)
        # Job exists and is completed (succeeded or failed); idempotent return
        return job_name

    container = V1Container(
        name="ingest",
        image=image,
        image_pull_policy="IfNotPresent",
        args=[project_path],
        env=[V1EnvVar(name="VECTOR_DB_URL", value=vector_db_url)],
    )
    template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(labels={"app": "code-helper-ingest"}),
        spec=V1PodSpec(restart_policy="OnFailure", containers=[container]),
    )
    job_spec = V1JobSpec(
        template=template,
        ttl_seconds_after_finished=3600,
        backoff_limit=2,
    )
    job = V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=V1ObjectMeta(name=job_name, labels={"app.kubernetes.io/name": "code-helper", "app.kubernetes.io/component": "ingest"}),
        spec=job_spec,
    )

    api.create_namespaced_job(namespace=namespace, body=job)
    return job_name
