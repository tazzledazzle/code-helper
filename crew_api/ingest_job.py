"""Create Kubernetes Jobs for code-helper ingest."""

import hashlib
import time

from kubernetes.client import BatchV1Api, V1Job, V1JobSpec, V1PodTemplateSpec, V1PodSpec, V1Container, V1ObjectMeta, V1EnvVar


def create(
    project_path: str,
    namespace: str,
    vector_db_url: str,
    image: str = "code-helper-ingest",
) -> str:
    """Create an ingest Job in the given namespace. Returns the Job name."""
    job_name = _job_name(project_path)

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

    api = BatchV1Api()
    api.create_namespaced_job(namespace=namespace, body=job)
    return job_name


def _job_name(project_path: str) -> str:
    """Generate a unique Job name: ingest-<hash>-<timestamp>."""
    h = hashlib.sha256(project_path.encode()).hexdigest()[:8]
    ts = int(time.time())
    return f"ingest-{h}-{ts}"
