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
import warnings

class Settings(BaseSettings):
    """Configuration settings for the application."""
    
    # Kubernetes settings
    kubernetes_api_url: str = "https://kubernetes.default.svc"
    kubernetes_token_path: str = "/var/run/secrets/kubernetes.io/serviceaccount/token"
    
    # Argo CD settings
    argo_cd_url: str = os.getenv("ARGO_CD_URL", "https://argo-cd-server.argo-cd.svc")
    argo_cd_username: str = os.getenv("ARGO_CD_USERNAME", "admin")
    argo_cd_password: str = os.getenv("ARGO_CD_PASSWORD", "")  # No default for security
    
    # TVP settings
    tvp_repo_url: str = os.getenv("TVP_REPO_URL", "git@github.com:your-org/kubernetes-apps.git")
    tvp_repo_path: str = os.getenv("TVP_REPO_PATH", "/tmp/kubernetes-apps")
    tvp_branch: str = os.getenv("TVP_BRANCH", "main")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    verify_ssl: bool = os.getenv("VERIFY_SSL", "true").lower() != "false"
    
    class Config:
        env_file = ".env"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._check_security_settings()
    
    def _check_security_settings(self):
        """Check and warn about insecure settings."""
        if not self.argo_cd_password:
            warnings.warn("Argo CD password not set. Please set ARGO_CD_PASSWORD environment variable.")
        if not self.verify_ssl:
            warnings.warn("SSL verification is disabled. This is insecure and should not be used in production.")

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
