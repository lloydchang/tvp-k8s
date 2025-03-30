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
import yaml

from config import get_settings, get_k8s_client

router = APIRouter()

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

# Direct ArgoCD Operations
@router.post("/applications/", summary="Create an ArgoCD application")
async def create_argocd_application(
    application: ArgoCDApplicationRequest,
    k8s_client: client.ApiClient = Depends(get_k8s_client)
):
    """
    Creates an Argo CD Application.
    
    Constructs a YAML manifest for an Argo CD Application using the provided details,
    then applies it to the Kubernetes cluster.
    """
    # Construct the Application YAML
    application_yaml = f"""
    apiVersion: argoproj.io/v1alpha1
    kind: Application
    metadata:
      name: {application.name}
      namespace: argocd
      finalizers:
      - resources-finalizer.argocd.argoproj.io
    spec:
      destination:
        namespace: {application.target_namespace}
        server: https://kubernetes.default.svc
      project: default
      source:
        path: {application.path}
        repoURL: {application.repo_url}
        targetRevision: {application.target_revision}
        directory:
          recurse: true
      syncPolicy:
        automated:
          prune: {str(application.sync_policy_prune).lower()}
          selfHeal: {str(application.sync_policy_self_heal).lower()}
        syncOptions:
        - CreateNamespace=true
    """

    try:
        from kubernetes import utils
        utils.create_from_yaml(k8s_client, yaml.safe_load(application_yaml))
        return {"message": f"Argo CD Application '{application.name}' created successfully."}
    except client.rest.ApiException as e:
        raise HTTPException(status_code=e.status, detail=f"Failed to create Argo CD Application: {e.reason}")

@router.post("/applications/{app_name}/sync", summary="Sync an ArgoCD application")
async def sync_argocd_application(app_name: str):
    """
    Triggers synchronization of an Argo CD application.
    """
    settings = get_settings()
    
    # Authenticate with ArgoCD
    async with httpx.AsyncClient(verify=False) as client:
        auth_response = await client.post(
            f"{settings.argocd_url}/api/v1/session",
            json={"username": settings.argocd_username, "password": settings.argocd_password},
        )
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="ArgoCD Authentication Failed")
        token = auth_response.json().get("token")
    
    # Trigger sync operation
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.post(
                f"{settings.argocd_url}/api/v1/applications/{app_name}/sync",
                headers=headers,
                json={"prune": True}
            )
            if response.status_code >= 400:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"ArgoCD sync failed: {response.text}"
                )
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"ArgoCD API error: {str(e)}")

# ArgoCD Pass-Through Proxy
@router.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def argocd_proxy(path: str, request: Request):
    """
    Proxies a client request to the ArgoCD API after authenticating.
    """
    settings = get_settings()
    
    # Authenticate with ArgoCD
    async with httpx.AsyncClient(verify=False) as client:
        auth_response = await client.post(
            f"{settings.argocd_url}/api/v1/session",
            json={"username": settings.argocd_username, "password": settings.argocd_password},
        )
        if auth_response.status_code != 200:
            raise HTTPException(status_code=401, detail="ArgoCD Authentication Failed")
        token = auth_response.json().get("token")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    
    # Forward the request to ArgoCD
    target_url = f"{settings.argocd_url}/api/v1/{path}"
    
    async with httpx.AsyncClient(verify=False) as client:
        try:
            body = await request.json() if request.method in ["POST", "PUT"] else None
            response = await client.request(request.method, target_url, headers=headers, json=body)
            return response.json()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Proxy error: {e}")
