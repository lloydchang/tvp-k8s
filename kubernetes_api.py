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

from config import get_settings, get_k8s_client

router = APIRouter()

# Models
class DeploymentRequest(BaseModel):
    name: str
    image: str
    replicas: int = 3
    namespace: str = "default"

# Direct Kubernetes Operations
@router.post("/deployments/", summary="Create a Kubernetes deployment")
async def create_deployment(
    deployment: DeploymentRequest,
    k8s_api: client.CoreV1Api = Depends(get_k8s_client)
):
    """
    Creates a Kubernetes deployment using the provided deployment details.
    
    Constructs a V1Deployment specification based on the input deployment request and creates the
    deployment in the specified namespace using the Kubernetes AppsV1 API.
    """
    deployment_spec = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=deployment.name),
        spec=client.V1DeploymentSpec(
            replicas=deployment.replicas,
            selector=client.V1LabelSelector(
                match_labels={"app": deployment.name},
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(
                    labels={"app": deployment.name},
                ),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name=deployment.name,
                            image=deployment.image,
                            ports=[client.V1ContainerPort(container_port=80)]
                        )
                    ]
                )
            )
        )
    )
    
    try:
        apps_v1 = client.AppsV1Api()
        response = apps_v1.create_namespaced_deployment(
            namespace=deployment.namespace, 
            body=deployment_spec
        )
        return {"status": "Deployment created", "details": response.to_dict()}
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Kubernetes API error: {e.reason}")

@router.get("/namespaces/", summary="List all namespaces")
async def list_namespaces(k8s_api: client.CoreV1Api = Depends(get_k8s_client)):
    """Lists all namespaces in the Kubernetes cluster."""
    try:
        namespaces = k8s_api.list_namespace()
        return [ns.metadata.name for ns in namespaces.items]
    except ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Kubernetes API error: {e.reason}")

# Kubernetes Pass-Through Proxy
async def proxy_request(target_url: str, method: str, request: Request, headers: dict = None):
    """
    Proxies an HTTP request to a target URL and returns its JSON response.
    """
    async with httpx.AsyncClient(verify=False) as client:
        try:
            # Forward request body if applicable
            body = await request.json() if request.method in ["POST", "PUT"] else None
            response = await client.request(method, target_url, headers=headers, json=body)
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Proxy error: {e}")

@router.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def k8s_proxy(path: str, request: Request):
    """
    Proxies a request to the Kubernetes API.
    
    Retrieves the Kubernetes service account token and constructs the target URL by
    appending the provided path to the base API URL.
    """
    settings = get_settings()
    
    # Get token (in-cluster) or use kubeconfig (local development)
    try:
        # For in-cluster deployment
        with open(settings.k8s_token_path, "r") as f:
            k8s_token = f.read().strip()
        headers = {
            "Authorization": f"Bearer {k8s_token}",
            "Accept": "application/json",
        }
    except:
        # For local development
        # Use kubeconfig approach - simplified for example
        k8s_client = get_k8s_client()
        headers = {
            "Accept": "application/json",
        }
    
    target_url = f"{settings.k8s_api_url}/api/v1/{path}"
    return await proxy_request(target_url, request.method, request, headers)
