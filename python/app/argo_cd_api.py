"""
Argo CD API Module

This module provides direct API operations and pass-through proxy functionality
for Argo CD application management.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Any
import httpx
from .config import get_settings, get_kubernetes_client

proxy = APIRouter()

try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required. Install it with 'pip install pyyaml'")

# Models
class ArgoCDApplicationRequest(BaseModel):
    name: str
    repo_url: str
    path: str
    target_namespace: str = "default"
    target_revision: str = "HEAD"
    sync_policy_automated: bool = True
    sync_policy_prune: bool = True
    sync_policy_self_heal: bool = True

async def get_argo_cd_token():
    """Helper function to get Argo CD authentication token."""
    settings = get_settings()
    
    # For development mode, return a mock token if environment is set to development
    if settings.environment == "development":
        print(f"[DEV MODE] Returning mock Argo CD token for {settings.argo_cd_username}")
        return "dev-mode-mock-token-for-testing-purposes-only"
    
    if not settings.argo_cd_password:
        raise HTTPException(status_code=500, detail="Argo CD password not configured")
    
    async with httpx.AsyncClient(verify=settings.verify_ssl) as client:
        try:
            response = await client.post(
                f"{settings.argo_cd_url}/api/v1/session",
                json={
                    "username": settings.argo_cd_username,
                    "password": settings.argo_cd_password
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401, 
                    detail=f"Argo CD Authentication Failed: {response.text}"
                )

            # Await the json() coroutine
            json_response = await response.json()
            return json_response.get("token")
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Argo CD service unavailable: {str(e)}"
            )

# Also provide the auth_token function as originally named for backward compatibility
get_argo_cd_auth_token = get_argo_cd_token

# Argo CD True Pass-Through Proxy
@proxy.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def argo_cd_proxy(path: str, request: Request):
    """
    Provides a true pass-through proxy to the Argo CD API.
    """
    settings = get_settings()
    
    # For development mode, return mock data
    if settings.environment == "development":
        print(f"[DEV MODE] Returning mock data for Argo CD path: {path}")
        
        # Handle different paths with appropriate mock data
        if path == "applications":
            return {
                "items": [
                    {
                        "metadata": {
                            "name": "example-app",
                            "namespace": "argocd"
                        },
                        "spec": {
                            "source": {
                                "repoURL": "https://github.com/example/example-app.git",
                                "path": ".",
                                "targetRevision": "HEAD"
                            },
                            "destination": {
                                "server": "https://kubernetes.default.svc",
                                "namespace": "default"
                            }
                        },
                        "status": {
                            "health": {"status": "Healthy"},
                            "sync": {"status": "Synced"}
                        }
                    }
                ]
            }
        # Mock response for projects endpoint
        elif path == "projects":
            return {
                "items": [
                    {
                        "metadata": {
                            "name": "default"
                        },
                        "spec": {
                            "description": "Default project"
                        }
                    }
                ]
            }
        # Generic mock response for other endpoints
        else:
            return {
                "path": path,
                "message": "Mock response in development mode",
                "status": "success"
            }
    
    token = await get_argo_cd_auth_token()

    # Create base headers with authentication
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # Forward all headers from the original request
    for header_key, header_value in request.headers.items():
        if header_key.lower() not in ["host", "connection", "content-length", "authorization"]:
            headers[header_key] = header_value
    
    # Create target URL
    target_url = f"{settings.argo_cd_url}/api/v1/{path}"
    
    # Pass through the request without modification
    async with httpx.AsyncClient(verify=settings.verify_ssl) as client:
        try:
            body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True
            )

            # Return the awaited json response
            return await response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Argo CD API unavailable: {str(e)}")
