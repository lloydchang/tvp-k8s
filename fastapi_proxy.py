# fastapi_proxy.py - FastAPI Proxy for Kubernetes & ArgoCD APIs

from fastapi import FastAPI, HTTPException, Request
import httpx
import os

app = FastAPI()

# Kubernetes API (Assumes in-cluster service account access)
K8S_API_URL = "https://kubernetes.default.svc"
K8S_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

# ArgoCD API URL and credentials
ARGOCD_URL = "https://argocd-server.argocd.svc"
ARGOCD_USERNAME = "admin"
ARGOCD_PASSWORD = "yourpassword"  # Use a secret manager in production!

# Read Kubernetes Service Account token
def get_k8s_token() -> str:
    """
    Retrieve the Kubernetes service account token.
    
    This function reads the token from the file specified by K8S_TOKEN_PATH and returns
    it as a stripped string. If the token cannot be read, it raises an HTTPException
    with a 500 status code.
    """
    try:
        with open(K8S_TOKEN_PATH, "r") as f:
            return f.read().strip()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Unable to read K8s token: {e}") from e

async def proxy_request(target_url: str, method: str, request: Request, headers: dict = None):
    """
    Proxies an HTTP request to a target URL and returns its JSON response.
    
    This asynchronous function forwards the incoming request using the specified HTTP method
    to the given target URL. For POST and PUT methods, it extracts the JSON body from the request
    and includes it in the proxied request. The operation uses an asynchronous HTTP client with SSL
    verification disabled. If an HTTP error occurs during the request, an HTTPException with a 500
    status code is raised.
        
    Args:
        target_url: The URL to which the request is proxied.
        method: The HTTP method (e.g., "GET", "POST", "PUT", "DELETE") to use.
        request: The incoming FastAPI request from which to extract the payload when applicable.
        headers: Optional headers to include in the proxied request.
        
    Returns:
        The JSON-decoded response from the target URL.
        
    Raises:
        HTTPException: If an HTTP error occurs during the proxied request.
    """
    async with httpx.AsyncClient(verify=False) as client:
        try:
            # Forward request body if applicable
            body = await request.json() if request.method in ["POST", "PUT"] else None
            response = await client.request(method, target_url, headers=headers, json=body)
            return response.json()
        except httpx.HTTPError as e:
except httpx.HTTPError as e:
    raise HTTPException(status_code=500, detail=f"Proxy error: {e}") from e

# ------------- Kubernetes Pass-Through Proxy -------------
@app.get("/k8s/{path:path}")
@app.post("/k8s/{path:path}")
@app.put("/k8s/{path:path}")
@app.delete("/k8s/{path:path}")
async def k8s_proxy(path: str, request: Request) -> dict:
    ...
    """
    Proxies a request to the Kubernetes API.
    
    Retrieves the Kubernetes service account token and constructs the target URL by
    appending the provided path to the base API URL. It sets the necessary Authorization
    and Accept headers and forwards the incoming request using its HTTP method.
    
    Args:
        path: The API endpoint segment to be appended to the base Kubernetes URL.
        request: The incoming HTTP request containing method and payload details.
    
    Returns:
        The JSON-decoded response from the Kubernetes API.
    
    Raises:
        HTTPException: If the Kubernetes token retrieval fails or the proxy request encounters an error.
    """
    k8s_token = get_k8s_token()
    headers = {
        "Authorization": f"Bearer {k8s_token}",
        "Accept": "application/json",
    }
    target_url = f"{K8S_API_URL}/api/v1/{path}"
    return await proxy_request(target_url, request.method, request, headers)

# ------------- ArgoCD Pass-Through Proxy -------------
@app.get("/argocd/{path:path}")
@app.post("/argocd/{path:path}")
@app.put("/argocd/{path:path}")
@app.delete("/argocd/{path:path}")
async def argocd_proxy(path: str, request: Request):
    """
    Proxies a client request to the ArgoCD API after authenticating.
    
    This function initiates an authentication request to ArgoCD using preset
    credentials. On successful authentication, it retrieves an access token and
    forwards the client request—preserving the HTTP method and body—to the
    specified ArgoCD API endpoint constructed from the provided path. If
    authentication fails, it raises an HTTPException with a 401 status code.
    
    Parameters:
        path: The relative API endpoint path to target (appended to /api/v1/).
        request: The incoming request to be proxied, including its method and body.
    
    Returns:
        The JSON-decoded response from the proxied ArgoCD API request.
    """
    # Authenticate with ArgoCD (simple login for example)
    async with httpx.AsyncClient(verify=False) as client:
        auth_response = await client.post(
            f"{ARGOCD_URL}/api/v1/session",
            json={"username": ARGOCD_USERNAME, "password": ARGOCD_PASSWORD},
        )
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="ArgoCD Authentication Failed")
        token = auth_response.json().get("token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    target_url = f"{ARGOCD_URL}/api/v1/{path}"
    return await proxy_request(target_url, request.method, request, headers)
