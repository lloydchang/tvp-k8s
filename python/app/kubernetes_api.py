"""
Kubernetes API Module

This module provides direct API operations and proxy functionality 
for Kubernetes resources.
"""

import os
import json
import base64
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
import httpx
import yaml
import aiofiles  # Add missing import
from kubernetes import client  # Ensure client is imported

from .config import get_settings, get_kubernetes_client

# Using APIRouter instead of APIProxy which doesn't exist in FastAPI
proxy = APIRouter()

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
@proxy.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
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
    
    # Determine headers - Try multiple methods to get auth token
    headers = {}
    
    # Method 1: Try async file read
    try:
        async with aiofiles.open(settings.kubernetes_token_path, "r") as f:
            kubernetes_token = (await f.read()).strip()
        headers["Authorization"] = f"Bearer {kubernetes_token}"
    except (FileNotFoundError, PermissionError):
        # Method 2: Try the synchronous method from config
        try:
            kubernetes_token = get_kubernetes_token()
            if kubernetes_token:
                headers["Authorization"] = f"Bearer {kubernetes_token}"
        except Exception as e:
            # In development, we'll continue without auth header
            if settings.environment != "development":
                raise HTTPException(status_code=401, detail=f"Kubernetes authentication failed: {str(e)}")
    
    # Forward all headers from the original request
    for header_key, header_value in request.headers.items():
        if header_key.lower() not in ["host", "connection", "content-length", "authorization"]:
            headers[header_key] = header_value
    
    # Create the target URL - use the kubernetes_api_url from settings
    api_base = settings.kubernetes_api_url.rstrip('/')
    
    # Check if path already includes api/v1 or apis prefix
    if path.startswith("api/") or path.startswith("apis/"):
        target_url = f"{api_base}/{path}"
    else:
        # Default to api/v1 for backward compatibility
        target_url = f"{api_base}/api/v1/{path}"
    
    # Debug logging (removed in production)
    if settings.environment == "development":
        print(f"Proxying {request.method} request to: {target_url}")
        
    # Pass through the request with appropriate timeout and error handling
    async with httpx.AsyncClient(verify=settings.verify_ssl, timeout=30.0) as client:
        try:
            body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=True,
            )
            
            # Check if the response is JSON
            try:
                return response.json()
            except ValueError:
                # Return text for non-JSON responses
                return {"raw_response": response.text, "status_code": response.status_code}
                
        except httpx.TimeoutException as e:
            raise HTTPException(status_code=504, detail=f"Kubernetes API timeout: {str(e)}")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=503, detail=f"Kubernetes API unavailable: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error connecting to Kubernetes API: {str(e)}")