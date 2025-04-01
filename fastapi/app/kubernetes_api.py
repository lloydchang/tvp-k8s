"""
Kubernetes API Module

This module provides direct API operations and pass-through proxy functionality
for Kubernetes cluster management.

Features:
- Transparent proxy to the Kubernetes API
- Authentication handling for cluster access
- Models for Kubernetes resource creation
- Helper functions for accessing the Kubernetes API clients
"""

from fastapi import APIProxy, Request, Depends, HTTPException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx

from config import get_settings, get_kubernetes_client

proxy = APIProxy()

# Models
class DeploymentRequest(BaseModel):
    """
    Model for Kubernetes deployment requests.
    
    Attributes:
        name (str): Name of the deployment.
        image (str): Container image to deploy.
        replicas (int): Number of replicas to maintain, defaults to 3.
        namespace (str): Target Kubernetes namespace, defaults to "default".
    """
    name: str
    image: str
    replicas: int = 3
    namespace: str = "default"

def get_apps_v1_client():
    """
    Returns a Kubernetes AppsV1Api client.
    
    This client provides access to Deployments, DaemonSets, StatefulSets, 
    and other app resources.
    
    Returns:
        kubernetes.client.AppsV1Api: Configured Kubernetes Apps V1 API client.
    """
    # Use the same configuration method as get_kubernetes_client
    get_kubernetes_client()  # This sets up the configuration
    return client.AppsV1Api()

# Kubernetes True Pass-Through Proxy
@proxy.api_route("/kubernetes/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def kubernetes_proxy(path: str, request: Request):
    """
    Provides a true pass-through proxy to the Kubernetes API.
    
    Forwards the incoming request to the Kubernetes API with proper authentication,
    preserving the HTTP method, headers, and body content.
    
    Args:
        path (str): The path component of the URL to forward to the Kubernetes API.
        request (Request): The incoming FastAPI request object.
        
    Returns:
        dict: The JSON response from the Kubernetes API.
        
    Raises:
        HTTPException: If the Kubernetes API is unavailable or returns an error.
    """
    settings = get_settings()
    
    # Determine headers
    try:
import aiofiles

try:
    async with aiofiles.open(settings.kubernetes_token_path, "r") as f:
        kubernetes_token = (await f.read()).strip()
            kubernetes_token = f.read().strip()
        headers = {
            "Authorization": f"Bearer {kubernetes_token}",
        }
    except FileNotFoundError:
        # For local development using kubeconfig
        headers = {}
    except PermissionError:
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
response = await client.request(
    method=request.method,
    url=target_url,
    headers=headers,
    content=body,
    follow_redirects=True,
)
            
            # Return the raw response
            return response.json()
        except httpx.HTTPError as e:
-            raise HTTPException(status_code=503, detail=f"Kubernetes API unavailable: {str(e)}")
+            raise HTTPException(status_code=503, detail=f"Kubernetes API unavailable: {str(e)}") from e
