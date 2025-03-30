from fastapi import FastAPI, Depends, HTTPException
from kubernetes import client, config

app = FastAPI()

def get_k8s_client():
    """
    Attempts to load the Kubernetes configuration and return a CoreV1Api client.
    
    If the configuration fails to load, raises an HTTPException with a 500 status code.
    """
    try:
        config.load_kube_config()  # Loads from ~/.kube/config or in-cluster config
    except client.config_exception.ConfigException as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Kubernetes config: {e}")
    return client.CoreV1Api()

@app.get("/namespaces")
async def list_namespaces(k8s_client: client.CoreV1Api = Depends(get_k8s_client)):
    """
    Lists all namespaces in the Kubernetes cluster.
    
    This asynchronous endpoint retrieves namespace names using the provided Kubernetes client.
    It calls the client's list_namespace method to obtain namespace items and returns a list
    of the namespace names. If the API call fails, an HTTPException is raised with the
    corresponding status code and error detail.
    """
    try:
        namespaces = k8s_client.list_namespace()
        return [ns.metadata.name for ns in namespaces.items]
    except client.ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Kubernetes API error: {e.reason}")

@app.get("/healthz")
async def health_check():
    """
    Check the health status of the service.
    
    Returns:
        dict: A JSON-compatible dictionary with a "status" key set to "ok".
    """
    return {"status": "ok"}

# Add more endpoints for deployments, services, etc.