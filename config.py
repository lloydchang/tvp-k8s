"""
Configuration Module

This module provides configuration settings and client initialization
for the Kubernetes Platform API.
"""

from functools import lru_cache
from pydantic import BaseSettings
from kubernetes import client, config
from fastapi import HTTPException
import os

class Settings(BaseSettings):
    """Configuration settings for the application."""
    
    # Kubernetes settings
    k8s_api_url: str = "https://kubernetes.default.svc"
    k8s_token_path: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    
    # ArgoCD settings
    argocd_url: str = "https://argocd-server.argocd.svc"
    argocd_username: str = "admin"
    argocd_password: str = "password"  # In production, use secrets
    
    # GitOps settings
    git_repo_url: str = "git@github.com:your-org/k8s-apps.git"
    git_repo_path: str = "/tmp/k8s-apps"
    git_branch: str = "main"
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    """
    Returns cached settings instance.
    """
    return Settings()

def get_k8s_client():
    """
    Retrieves a Kubernetes API client.
    
    This function attempts to load the in-cluster Kubernetes configuration.
    If that fails, it falls back to loading the local kube config file.
    """
    try:
        # Try to load in-cluster config (when running inside a pod)
        config.load_incluster_config()
    except config.ConfigException:
        # Fall back to local kubeconfig for development
        try:
            config.load_kube_config()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load Kubernetes config: {e}")
    
    return client.CoreV1Api()

def get_k8s_token():
    """
    Retrieve the Kubernetes service account token.
    
    This function reads the token from the file specified by K8S_TOKEN_PATH and returns
    it as a stripped string. If the token cannot be read, it raises an HTTPException
    with a 500 status code.
    """
    settings = get_settings()
    try:
        with open(settings.k8s_token_path, "r") as f:
            return f.read().strip()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Unable to read K8s token: {e}")
