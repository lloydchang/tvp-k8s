from fastapi import FastAPI, Request, HTTPException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import httpx
import yaml

app = FastAPI(title="Kubernetes Platform with Pass-Through")

# Kubernetes Client Configuration
def get_k8s_client():
    """
    Retrieves and configures the Kubernetes API client.
    
    This function attempts to load the in-cluster Kubernetes configuration. If that fails,
    it falls back to loading the local kube config file. It returns the configured Kubernetes
    client module.
    """
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
    Proxies HTTP requests to the Kubernetes API.
    
    This asynchronous endpoint dynamically selects the appropriate Kubernetes API client
    based on the resource indicated by full_path (e.g., namespaces, deployments, or others).
    It extracts the HTTP method and, for non-GET/HEAD requests, the JSON body. The method name
    is determined by the HTTP verb—with PUT requests translated to PATCH—and is dynamically
    invoked on the selected API client. The response from the Kubernetes API is returned as a
    dictionary containing the status code, headers, and a YAML-parsed body.
    
    Args:
        full_path: URL path segment specifying the target Kubernetes API resource.
        request: The incoming HTTP request.
    
    Returns:
        A dictionary with keys 'status_code', 'headers', and 'body' representing the API response.
    
    Raises:
        HTTPException: If an error occurs during the Kubernetes API call.
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
    Proxies requests to the ArgoCD API.
    
    Extracts the HTTP method and JSON payload (if applicable) from the incoming
    request, then forwards the request to the ArgoCD server's API endpoint with the
    required authorization and content type headers. Returns a dictionary containing
    the response status code, headers, and JSON body.
    
    Raises:
        HTTPException: If the HTTP request to the ArgoCD API fails.
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
    """
    Return platform-level details including supported APIs and capabilities.
    
    Returns:
        dict: A dictionary containing the platform's details:
            - platform_name: The name of the platform.
            - supported_apis: A list of APIs supported by the platform.
            - capabilities: A list describing the platform's features.
    """
    return {
        "platform_name": "Kubernetes Passthrough Platform",
        "supported_apis": ["kubernetes", "argocd"],
        "capabilities": [
            "direct_api_passthrough",
            "deployment_management",
            "cluster_interaction"
        ]
    }
