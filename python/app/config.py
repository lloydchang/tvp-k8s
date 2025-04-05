"""
Configuration Module

This module provides configuration settings and client initialization
for the Kubernetes Platform API.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from kubernetes import client, config
from fastapi import HTTPException
import os
import warnings

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Kubernetes settings
    kubernetes_api_url: str = "https://kubernetes.default.svc"
    kubernetes_token_path: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    
    # Argo CD settings
    argo_cd_url: str = os.getenv("ARGO_CD_URL", "https://argo-cd-server.argo-cd.svc")
    argo_cd_username: str = os.getenv("ARGO_CD_USERNAME", "admin")
    argo_cd_password: str = os.getenv("ARGO_CD_PASSWORD", "")  # No default for security
    
    # Property to support the tests - this will be the same as argo_cd_username
    # but is needed for backward compatibility with tests
    @property
    def argo_cd_identity(self) -> str:
        return self.argo_cd_username
    
    # TVP settings
    tvp_repo_url: str = os.getenv("TVP_REPO_URL", "https://github.com/lloydchang/tvp.git")
    tvp_repo_path: str = os.getenv("TVP_REPO_PATH", "/tmp/kubernetes-apps")
    tvp_branch: str = os.getenv("TVP_BRANCH", "main")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    verify_ssl: bool = True
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.verify_ssl:
            raise ValueError("SSL verification must remain enabled for security.")

@lru_cache()
def get_settings():
    """
    Returns cached settings instance.
    """
    return Settings()

def get_kubernetes_client():
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
            raise HTTPException(status_code=500, detail=f"Failed to load Kubernetes config: {e}") from e

    return client.CoreV1Api()
def get_kubernetes_token():
    """
    Retrieve the Kubernetes service account token.
    
    This function reads the token from the file specified by kubernetes_token_path and returns
    it as a stripped string. If the token cannot be read, it raises an HTTPException
    with a 500 status code.
    """
    settings = get_settings()
    try:
        with open(settings.kubernetes_token_path, "r") as f:
            return f.read().strip()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Unable to read kubernetes token: {e}")
