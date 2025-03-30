"""
ArgoCD API Module

This module provides direct API operations and pass-through proxy functionality
for ArgoCD application management.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from kubernetes import client
from typing import Optional, Dict, Any, List
import httpx

from config import get_settings, get_k8s_client

router = APIRouter()

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

async def get_argocd_token():
    """Helper function to get ArgoCD authentication token."""
    settings = get_settings()
    
    if not settings.argocd_password:
        raise HTTPException(status_code=500, detail="ArgoCD password not configured")
    
    async with httpx.AsyncClient(verify=settings.verify_ssl) as client:
        try:
            auth_response = await client.post(
                f"{settings.argocd_url}/api/v1/session",
                json={"username": settings.argocd_username, "password": settings.argocd_password},
                timeout=10.0  # Add reasonable timeout
            )
            if auth_response.status_code != 200:
                raise HTTPException(
                    status_code=401, 
                    detail=f"ArgoCD Authentication Failed: {auth_response.text}"
                )
            return auth_response.json().get("token")
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"ArgoCD service unavailable: {str(e)}")

# ArgoCD True Pass-Through Proxy
@router.api_route("/argocd/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def argocd_proxy(path: str, request: Request):
    """
    Provides a true pass-through proxy to the ArgoCD API.
    """
    settings = get_settings()
    token = await get_argocd_token()

    # Create base headers with authentication
    headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # Forward all headers from the original request
    for header_key, header_value in request.headers.items():
        if header_key.lower() not in ["host", "connection", "content-length", "authorization"]:
            headers[header_key] = header_value
    
    # Create target URL
    target_url = f"{settings.argocd_url}/api/v1/{path}"
    
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
            
            # Return the raw response
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"ArgoCD API unavailable: {str(e)}")
