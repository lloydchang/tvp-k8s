from fastapi import FastAPI, Depends, HTTPException
from kubernetes import client, config

app = FastAPI()

def get_k8s_client():
    """
    Loads Kubernetes configuration and returns a CoreV1Api client.
    
    Attempts to load the Kubernetes configuration from the default kubeconfig file or in-cluster settings.
    Raises an HTTPException with status code 500 if the configuration cannot be loaded.
    """
    try:
        config.load_kube_config()  # Loads from ~/.kube/config or in-cluster config
    except client.config_exception.ConfigException as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Kubernetes config: {e}")
    return client.CoreV1Api()

@app.get("/namespaces")
async def list_namespaces(k8s_client: client.CoreV1Api = Depends(get_k8s_client)):
    """Retrieves the names of all namespaces in the Kubernetes cluster.
    
    This asynchronous endpoint uses the Kubernetes client to query for available namespaces and
    returns a list of their names. If the Kubernetes API call fails, an HTTPException is raised
    with the corresponding error status and message.
    """
    try:
        namespaces = k8s_client.list_namespace()
        return [ns.metadata.name for ns in namespaces.items]
    except client.ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Kubernetes API error: {e.reason}")

@app.get("/healthz")
async def health_check():
    """
    Check application health and return status.
    
    Returns:
        dict: A dictionary with a "status" key set to "ok", indicating the service is healthy.
    """
    return {"status": "ok"}

# Add more endpoints for deployments, services, etc.