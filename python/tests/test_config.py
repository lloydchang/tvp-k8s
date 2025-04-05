import pytest
from unittest.mock import patch, MagicMock, mock_open
import os
from fastapi import HTTPException
from kubernetes import config

def test_settings_initialization():
    """Test initializing Settings with default values"""
    from python.app.config import Settings
    
    # Create settings with default values
    settings = Settings()
    
    # Verify default values
    assert settings.kubernetes_api_url == "https://kubernetes.default.svc"
    assert settings.kubernetes_token_path == "/var/run/secrets/kubernetes.io/serviceaccount/token"
    assert settings.argo_cd_url is not None
    assert settings.argo_cd_username is not None
    assert settings.gitops_repo_url is not None
    assert settings.gitops_repo_path is not None
    assert settings.gitops_repo_branch is not None
    assert settings.environment is not None
    assert settings.verify_ssl is True

def test_settings_argo_cd_identity_property():
    """Test the argo_cd_identity property of Settings"""
    from python.app.config import Settings
    
    settings = Settings(argo_cd_username="test-user")
    assert settings.argo_cd_identity == "test-user"
    
    # Test with a different username
    settings = Settings(argo_cd_username="another-user")
    assert settings.argo_cd_identity == "another-user"

def test_settings_verify_ssl_validation():
    """Test that verify_ssl cannot be disabled"""
    from python.app.config import Settings
    
    # Test initializing with verify_ssl=False should raise ValueError
    with pytest.raises(ValueError) as excinfo:
        Settings(verify_ssl=False)
    
    assert "SSL verification must remain enabled" in str(excinfo.value)

def test_get_settings_cache():
    """Test that get_settings uses lru_cache"""
    from python.app.config import get_settings
    
    # Call get_settings multiple times
    settings1 = get_settings()
    settings2 = get_settings()
    
    # Verify it's the same object (cached)
    assert settings1 is settings2

def test_get_kubernetes_client_incluster():
    """Test getting Kubernetes client with in-cluster config"""
    from python.app.config import get_kubernetes_client
    
    # Mock in-cluster config loading
    with patch("kubernetes.config.load_incluster_config") as mock_load_incluster:
        with patch("kubernetes.client.CoreV1Api") as mock_api:
            mock_api.return_value = MagicMock()
            
            # Call the function
            client = get_kubernetes_client()
            
            # Verify in-cluster config was attempted
            mock_load_incluster.assert_called_once()
            # Verify client was created
            mock_api.assert_called_once()
            
            # Verify the client is the mock we created
            assert client == mock_api.return_value

def test_get_kubernetes_client_kubeconfig():
    """Test getting Kubernetes client with local kubeconfig fallback"""
    from python.app.config import get_kubernetes_client
    
    # Mock in-cluster config failing and kubeconfig succeeding
    with patch("kubernetes.config.load_incluster_config") as mock_load_incluster:
        mock_load_incluster.side_effect = config.ConfigException("No in-cluster config")
        
        with patch("kubernetes.config.load_kube_config") as mock_load_kubeconfig:
            with patch("kubernetes.client.CoreV1Api") as mock_api:
                mock_api.return_value = MagicMock()
                
                # Call the function
                client = get_kubernetes_client()
                
                # Verify in-cluster config was attempted
                mock_load_incluster.assert_called_once()
                # Verify kubeconfig was loaded
                mock_load_kubeconfig.assert_called_once()
                # Verify client was created
                mock_api.assert_called_once()
                
                # Verify the client is the mock we created
                assert client == mock_api.return_value

def test_get_kubernetes_client_both_fail():
    """Test getting Kubernetes client when both config methods fail"""
    from python.app.config import get_kubernetes_client
    
    # Mock both in-cluster and kubeconfig failing
    with patch("kubernetes.config.load_incluster_config") as mock_load_incluster:
        mock_load_incluster.side_effect = config.ConfigException("No in-cluster config")
        
        with patch("kubernetes.config.load_kube_config") as mock_load_kubeconfig:
            mock_load_kubeconfig.side_effect = Exception("No kubeconfig found")
            
            # Call the function and expect HTTPException
            with pytest.raises(HTTPException) as excinfo:
                get_kubernetes_client()
            
            # Verify error message and status code
            assert excinfo.value.status_code == 500
            assert "Failed to load Kubernetes config" in excinfo.value.detail

def test_get_kubernetes_token():
    """Test getting Kubernetes token from file"""
    from python.app.config import get_kubernetes_token
    
    token_content = "test-kubernetes-token\n"
    
    # Mock get_settings
    with patch("python.app.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.kubernetes_token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
        mock_get_settings.return_value = settings
        
        # Mock file open operation
        with patch("builtins.open", mock_open(read_data=token_content)):
            # Call the function
            token = get_kubernetes_token()
            
            # Verify token is the expected stripped value
            assert token == "test-kubernetes-token"

def test_get_kubernetes_token_file_error():
    """Test getting Kubernetes token when file cannot be read"""
    from python.app.config import get_kubernetes_token
    
    # Mock get_settings
    with patch("python.app.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.kubernetes_token_path = "/non-existent/path"
        mock_get_settings.return_value = settings
        
        # Mock file open operation to raise OSError
        with patch("builtins.open") as mock_file:
            mock_file.side_effect = OSError("File not found")
            
            # Call the function and expect HTTPException
            with pytest.raises(HTTPException) as excinfo:
                get_kubernetes_token()
            
            # Verify error message and status code
            assert excinfo.value.status_code == 500
            assert "Unable to read kubernetes token" in excinfo.value.detail