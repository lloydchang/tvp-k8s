from fastapi import FastAPI, Depends, HTTPException
from kubernetes import client, config

app = FastAPI()

def get_k8s_client():
    """Load Kubernetes configuration and return the API client."""
    try:
        config.load_kube_config()  # Loads from ~/.kube/config or in-cluster config
    except client.config_exception.ConfigException as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Kubernetes config: {e}")
    return client.CoreV1Api()

@app.get("/namespaces")
async def list_namespaces(k8s_client: client.CoreV1Api = Depends(get_k8s_client)):
    """Lists all namespaces in the Kubernetes cluster."""
    try:
        namespaces = k8s_client.list_namespace()
        return [ns.metadata.name for ns in namespaces.items]
    except client.ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Kubernetes API error: {e.reason}")

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Add more endpoints for deployments, services, etc.