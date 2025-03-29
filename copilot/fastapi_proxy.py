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
def get_k8s_token():
    try:
        with open(K8S_TOKEN_PATH, "r") as f:
            return f.read().strip()
    except Exception:
        raise HTTPException(status_code=500, detail="Unable to read K8s token")

async def proxy_request(target_url: str, method: str, request: Request, headers: dict = None):
    """Handles proxying requests to Kubernetes or ArgoCD"""
    async with httpx.AsyncClient(verify=False) as client:
        try:
            # Forward request body if applicable
            body = await request.json() if request.method in ["POST", "PUT"] else None
            response = await client.request(method, target_url, headers=headers, json=body)
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# ------------- Kubernetes Pass-Through Proxy -------------
@app.get("/k8s/{path:path}")
@app.post("/k8s/{path:path}")
@app.put("/k8s/{path:path}")
@app.delete("/k8s/{path:path}")
async def k8s_proxy(path: str, request: Request):
    """Pass-through requests to Kubernetes API"""
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
    """Pass-through requests to ArgoCD API"""
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
