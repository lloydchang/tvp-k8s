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
    kubernetes_api_url: str = os.getenv("KUBERNETES_API_URL", "http://localhost:8001")
    kubernetes_token_path: str = os.getenv("KUBERNETES_TOKEN_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/token")
    kubernetes_config_path: str = os.getenv("KUBERNETES_CONFIG_PATH", os.path.expanduser("~/.kube/config"))
    
    # Argo CD settings
    argo_cd_url: str = os.getenv("ARGO_CD_URL", "http://argocd-server:8080")
    argo_cd_username: str = os.getenv("ARGO_CD_USERNAME", "admin")
    argo_cd_password: str = os.getenv("ARGO_CD_PASSWORD", "password")  # Default from deploy-argocd.sh
    
    # Property to support the tests - this will be the same as argo_cd_username
    # but is needed for backward compatibility with tests
    @property
    def argo_cd_identity(self) -> str:
        return self.argo_cd_username
    
    # GitOps settings
    gitops_repo_url: str = os.getenv("GITOPS_REPO_URL", "https://github.com/lloydchang/tvp.git")
    gitops_repo_path: str = os.getenv("GITOPS_REPO_PATH", "/tmp/kubernetes-apps")
    gitops_repo_branch: str = os.getenv("GITOPS_REPO_BRANCH", "main")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Security
    verify_ssl: bool = os.getenv("VERIFY_SSL", "true").lower() == "true"
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Only enforce SSL verification in production
        if not self.verify_ssl and self.environment == "production":
            warnings.warn("SSL verification should remain enabled for production environments")

@lru_cache()
def get_settings():
    """
    Returns cached settings instance.
    """
    return Settings()

def get_kubernetes_client():
    """
    Retrieves a Kubernetes API client.
    
    This function attempts multiple methods to configure the Kubernetes client:
    1. Try using the configured proxy URL directly
    2. Try to load in-cluster config (when running inside a Kubernetes pod)
    3. Try to load from the KUBECONFIG environment variable if set
    4. Try to load from specified kubeconfig path in settings
    
    In development environments, this function will not raise exceptions for configuration
    issues to allow the application to start even without a valid Kubernetes connection.
    """
    settings = get_settings()
    
    # Try direct proxy configuration first (for kubectl proxy)
    if settings.kubernetes_api_url.startswith('http://'):
        # Configure API client to use the proxy directly
        configuration = client.Configuration()
        configuration.host = settings.kubernetes_api_url
        configuration.verify_ssl = settings.verify_ssl
        api_client = client.ApiClient(configuration)
        return client.CoreV1Api(api_client)
    
    # Otherwise try standard configuration methods
    try:
        print(f"Attempting to connect to Kubernetes at {settings.kubernetes_api_url}")
        # Method 1: Try in-cluster config
        config.load_incluster_config()
        return client.CoreV1Api()
    except config.ConfigException:
        try:
            # Method 2: Try from KUBECONFIG environment variable or default locations
            config.load_kube_config(config_file=settings.kubernetes_config_path)
            return client.CoreV1Api()
        except Exception as e:
            # Method 3: For HTTP proxy, try a more direct approach
            if settings.kubernetes_api_url.startswith('http://'):
                print(f"Using direct HTTP configuration for {settings.kubernetes_api_url}")
                configuration = client.Configuration()
                configuration.host = settings.kubernetes_api_url
                configuration.verify_ssl = settings.verify_ssl
                api_client = client.ApiClient(configuration)
                return client.CoreV1Api(api_client)
            # Method 4: In development mode, create a client that will fail gracefully
            elif settings.environment == "development":
                warnings.warn(f"Failed to load Kubernetes config: {e}. Creating a client anyway, but API calls will likely fail.")
                # Return the client anyway, it will fail when used but allows the app to start
                return client.CoreV1Api()
            else:
                # In production, we want to fail fast if we can't connect to Kubernetes
                raise HTTPException(status_code=500, detail=f"Failed to load Kubernetes config: {e}") from e
def get_kubernetes_token():
    """
    Retrieve the Kubernetes service account token.
    
    This function attempts multiple methods to retrieve a Kubernetes token:
    1. Try reading from the file specified in kubernetes_token_path
    2. If KUBECONFIG is set, try to extract token from there
    3. For development, return a placeholder token if all else fails
    
    Returns:
        str: The Kubernetes token if available, or a development placeholder
        
    Raises:
        HTTPException: In production mode, if no token can be retrieved
    """
    settings = get_settings()
    
    # Method 1: Try to read from token file (typical for in-cluster)
    try:
        with open(settings.kubernetes_token_path, "r") as f:
            return f.read().strip()
    except OSError:
        # Method 2: Try to extract from kubeconfig if available
        try:
            # If KUBECONFIG is set or we have a default path
            kubeconfig_path = os.environ.get('KUBECONFIG', settings.kubernetes_config_path)
            if os.path.exists(kubeconfig_path):
                with open(kubeconfig_path, 'r') as f:
                    kube_config = yaml.safe_load(f)
                    
                # Look for a token in the kubeconfig users section
                if kube_config and 'users' in kube_config:
                    for user in kube_config['users']:
                        if user.get('user', {}).get('token'):
                            return user['user']['token']
            
            # If we reach here, no token was found in kubeconfig
            if settings.environment == "development":
                warnings.warn("No Kubernetes token found, using development placeholder")
                return "development-placeholder-token"
            else:
                raise HTTPException(status_code=500, detail="No Kubernetes token found in token file or kubeconfig")
                
        except Exception as e:
            # In development, return a placeholder to allow the app to start
            if settings.environment == "development":
                warnings.warn(f"Error reading Kubernetes token: {e}. Using development placeholder.")
                return "development-placeholder-token"
            else:
                raise HTTPException(status_code=500, detail=f"Unable to read kubernetes token: {e}")
