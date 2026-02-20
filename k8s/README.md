# code-helper Kubernetes manifests

Cloud-portable manifests (no AWS/GCP-specific annotations). For local [kind](https://kind.sigs.k8s.io/) or [minikube](https://minikube.sigs.k8s.io/), use `imagePullPolicy: IfNotPresent` and load images after building.

## Apply (local kind/minikube)

1. **Create namespace and resources**
   ```bash
   kubectl apply -f k8s/
   ```
   All manifests include `namespace: code-helper` where needed. To apply in order:
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/crew-api-deployment.yaml
   kubectl apply -f k8s/runner-deployment.yaml
   kubectl apply -f k8s/vector-db-deployment.yaml
   kubectl apply -f k8s/services.yaml
   kubectl apply -f k8s/ingress.yaml   # optional
   ```

2. **Load local images (kind)**
   ```bash
   kind load docker-image code-helper-crew code-helper-runner code-helper-ingest --name <your-cluster-name>
   docker pull chromadb/chroma:latest
   kind load docker-image chromadb/chroma:latest --name <your-cluster-name>
   ```

3. **Port-forward crew-api and verify**
   ```bash
   kubectl port-forward -n code-helper svc/crew-api 8000:8000
   curl http://localhost:8000/health
   ```
   Expected: `{"status":"ok"}`

## Port-forward (no Ingress)

If you don't use Ingress, access services with port-forward:

- **Crew API**
  ```bash
  kubectl port-forward -n code-helper svc/crew-api 8000:8000
  curl http://localhost:8000/health
  ```
- **Runner** (e.g. for direct /execute calls)
  ```bash
  kubectl port-forward -n code-helper svc/runner 8080:8080
  ```
- **Chroma** (vector DB, e.g. for debugging)
  ```bash
  kubectl port-forward -n code-helper svc/chroma 8001:8000
  ```

## Ingest Job (template)

`ingest-job.yaml` is a static example. The Crew API will create Jobs from this spec dynamically (Task 18). To run the example once:

```bash
kubectl apply -f k8s/ingest-job.yaml -n code-helper
kubectl get jobs -n code-helper
kubectl logs -n code-helper job/code-helper-ingest-example -f
```

Override `args` (e.g. `["/workspace/my-project"]`) when creating the Job; env `VECTOR_DB_URL` comes from the crew-api ConfigMap.
