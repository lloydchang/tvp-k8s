from fastapi import FastAPI, Request, HTTPException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import httpx
import yaml

app = FastAPI(title="Kubernetes Platform with Pass-Through")

# Kubernetes Client Configuration
def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client

# ArgoCD Configuration
ARGOCD_SERVER = "https://argocd.yourcluster.com"
ARGOCD_TOKEN = "your-argocd-token"  # Consider using secure secret management

@app.api_route("/k8s/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def kubernetes_passthru(full_path: str, request: Request):
    """
    Pass-through endpoint for Kubernetes API
    Allows direct proxying of Kubernetes API requests
    """
    k8s_client = get_k8s_client()
    
    # Extract method and body
    method = request.method.lower()
    body = await request.json() if request.method not in ['GET', 'HEAD'] else None
    
    try:
        # Dynamic API client selection based on path
        if 'namespaces' in full_path:
            api_instance = client.CoreV1Api()
        elif 'deployments' in full_path:
            api_instance = client.AppsV1Api()
        else:
            # Generic API client for other resources
            api_instance = client.CustomObjectsApi()
        
        # Dynamically call the appropriate method
        response = getattr(api_instance, f"{'patch' if method == 'put' else method}_" + 
                           full_path.replace('/', '_').replace('-', '_'))(
            body=body,
            _preload_content=False
        )
        
        return {
            "status_code": response.status,
            "headers": dict(response.headers),
            "body": yaml.safe_load(response.data)
        }
    
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=str(e))

@app.api_route("/argocd/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def argocd_passthru(full_path: str, request: Request):
    """
    Pass-through endpoint for ArgoCD API
    Allows direct proxying of ArgoCD API requests
    """
    method = request.method.lower()
    body = await request.json() if request.method not in ['GET', 'HEAD'] else None
    
    headers = {
        "Authorization": f"Bearer {ARGOCD_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method.upper(), 
                f"{ARGOCD_SERVER}/api/v1/{full_path}", 
                headers=headers,
                json=body
            )
            
            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json()
            }
        
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=str(e))

# Additional utility endpoints
@app.get("/platform/info")
async def platform_info():
    """Provide platform-level information and capabilities"""
    return {
        "platform_name": "Kubernetes Passthrough Platform",
        "supported_apis": ["kubernetes", "argocd"],
        "capabilities": [
            "direct_api_passthrough",
            "deployment_management",
            "cluster_interaction"
        ]
    }
