"""
Kubernetes API Module

This module provides direct API operations and pass-through proxy functionality
for Kubernetes cluster management.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx

from config import get_settings, get_kubernetes_client

router = APIRouter()

# Models
class DeploymentRequest(BaseModel):
    name: str
    image: str
    replicas: int = 3
    namespace: str = "default"

def get_apps_v1_client():
    """
    Returns a Kubernetes AppsV1Api client.
    """
    # Use the same configuration method as get_kubernetes_client
    get_kubernetes_client()  # This sets up the configuration
    return client.AppsV1Api()

# Kubernetes True Pass-Through Proxy
@router.api_route("/kubernetes/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def kubernetes_proxy(path: str, request: Request):
    """
    Provides a true pass-through proxy to the Kubernetes API.
    """
    settings = get_settings()
    
    # Determine headers
    try:
        with open(settings.kubernetes_token_path, "r") as f:
            kubernetes_token = f.read().strip()
        headers = {
            "Authorization": f"Bearer {kubernetes_token}",
        }
    except:
        # For local development using kubeconfig
        headers = {}
    
    # Forward all headers from the original request
    for header_key, header_value in request.headers.items():
        if header_key.lower() not in ["host", "connection", "content-length"]:
            headers[header_key] = header_value
    
    # Create the target URL
    target_url = f"{settings.kubernetes_api_url}/api/v1/{path}"
    
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
            raise HTTPException(status_code=503, detail=f"Kubernetes API unavailable: {str(e)}")
