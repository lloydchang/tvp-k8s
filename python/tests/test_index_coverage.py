"""
Test file specifically targeting coverage gaps in app/index.py
"""

import pytest
import socket
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from starlette.testclient import TestClient
import sys
import os

# Import directly since pytest should handle paths with conftest.py
from app.index import app, health_check, root
from app.config import get_settings, Settings

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_health_check_development_mode():
    """Test health check in development mode with kubectl available."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "development"
    mock_settings.verify_ssl = False
    
    # Mock subprocess to simulate kubectl available
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('subprocess.run') as mock_run:
        
        # Mock successful kubectl get nodes
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "node1\nnode2"
        
        result = await health_check()
        
        assert result["status"] == "healthy"
        assert result["services"]["kubernetes"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_development_mode_no_kubectl():
    """Test health check in development mode with kubectl not available."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "development"
    mock_settings.verify_ssl = False
    
    # Mock subprocess to simulate kubectl not available
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('subprocess.run') as mock_run:
        
        mock_run.side_effect = FileNotFoundError("No kubectl")
        
        result = await health_check()
        
        assert "services" in result
        assert result["services"]["kubernetes"]["status"] == "unhealthy"
        assert "dev_mode" in result["services"]["kubernetes"]

@pytest.mark.asyncio
async def test_health_check_development_mode_kubectl_error():
    """Test health check in development mode with kubectl returning error."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "development"
    mock_settings.verify_ssl = False
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('subprocess.run') as mock_run:
        
        # First call fails (get nodes)
        mock_run.side_effect = [
            # kubectl get nodes fails
            MagicMock(returncode=1, stdout=""),
            # kubectl config current-context succeeds
            MagicMock(returncode=0, stdout="test-context")
        ]
        
        result = await health_check()
        
        assert result["services"]["kubernetes"]["status"] == "unhealthy"
        assert "test-context" in result["services"]["kubernetes"]["error"]

@pytest.mark.asyncio
async def test_health_check_development_mode_kubectl_timeout():
    """Test health check in development mode with kubectl timing out."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "development"
    mock_settings.verify_ssl = False
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('subprocess.run') as mock_run:
        
        mock_run.side_effect = subprocess.SubprocessError("Timeout")
        
        result = await health_check()
        
        assert result["services"]["kubernetes"]["status"] == "unhealthy"
        assert "optional" in result["services"]["kubernetes"]["error"]
        
@pytest.mark.asyncio
async def test_health_check_production_mode():
        """Test health check in production mode with HTTP client."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.environment = "production"
        mock_settings.verify_ssl = False
        mock_settings.kubernetes_api_url = "http://kube-api.test"
        mock_settings.argo_cd_url = "http://argocd.test"
        
        # Create two different client mocks for each call
        mock_client_k8s = AsyncMock()
        mock_response_k8s = MagicMock()
        mock_response_k8s.status_code = 200
        mock_client_k8s.__aenter__.return_value.get.return_value = mock_response_k8s
        
        mock_client_argo = AsyncMock()
        mock_response_argo = MagicMock()
        mock_response_argo.status_code = 200
        mock_client_argo.__aenter__.return_value.get.return_value = mock_response_argo
        
        with patch('app.index.get_settings', return_value=mock_settings), \
             patch('httpx.AsyncClient', side_effect=[mock_client_k8s, mock_client_argo]):
            
            result = await health_check()
            
            assert result["status"] == "healthy"
            assert result["services"]["kubernetes"]["status"] == "healthy"
            assert result["services"]["argo_cd"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_production_mode_api_error():
    """Test health check in production mode with API error."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "production"
    mock_settings.verify_ssl = False
    mock_settings.kubernetes_api_url = "http://kube-api.test"
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"
    mock_client.__aenter__.return_value.get.return_value = mock_response
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        result = await health_check()
        
        assert result["status"] == "degraded"
        assert result["services"]["kubernetes"]["status"] == "unhealthy"
        assert "500" in result["services"]["kubernetes"]["error"]

@pytest.mark.asyncio
async def test_health_check_production_mode_connection_error():
    """Test health check in production mode with connection error."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "production"
    mock_settings.verify_ssl = False
    mock_settings.kubernetes_api_url = "http://kube-api.test"
    
    # Mock client to raise exception
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.side_effect = Exception("Connection error")
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        result = await health_check()
        
        assert result["status"] == "degraded"
        assert result["services"]["kubernetes"]["status"] == "unhealthy"
        assert "Connection error" in result["services"]["kubernetes"]["error"]
        
@pytest.mark.asyncio
async def test_health_check_dev_mode_additional_diagnostics():
        """Test health check in development mode with additional diagnostics."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.environment = "development"
        mock_settings.verify_ssl = False
        
        # First call fails with exception, then try diagnostics
        with patch('app.index.get_settings', return_value=mock_settings), \
             patch('subprocess.run') as mock_run, \
             patch('httpx.AsyncClient') as mock_client:
            
            # Make the HTTP call raise exception
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("HTTP client error")
            
            # Then make the diagnostic kubectl version call succeed
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Client Version: v1.21.0"
            
            result = await health_check()
            
            assert "kubernetes" in result["services"]
            # In development mode with a working kubectl, the status should be healthy
            # as the health check can get diagnostic information instead of reporting an error
            assert result["services"]["kubernetes"]["status"] == "healthy"
            assert "Connected to Kubernetes cluster" in result["services"]["kubernetes"]["message"]
            
@pytest.mark.asyncio
async def test_health_check_dev_mode_no_diagnostic_tools():
        """Test health check in development mode with no diagnostic tools."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.environment = "development"
        mock_settings.verify_ssl = False
        
        # First call fails with exception, diagnostic tools also fail
        with patch('app.index.get_settings', return_value=mock_settings), \
             patch('subprocess.run') as mock_run, \
             patch('httpx.AsyncClient') as mock_client:
            
            # Make the HTTP call raise exception
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("HTTP client error")
            
            # Make the diagnostic tool call fail
            mock_run.side_effect = FileNotFoundError("No kubectl installed")
            
            result = await health_check()
            
            assert result["services"]["kubernetes"]["status"] == "unhealthy"
            # The actual error message might be slightly different, check for a portion
            assert "tools not" in result["services"]["kubernetes"]["error"] and "optional" in result["services"]["kubernetes"]["error"]

@pytest.mark.asyncio
async def test_health_check_argocd_dev_mode():
    """Test health check for ArgoCD in development mode."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "development"
    mock_settings.verify_ssl = False
    mock_settings.argo_cd_url = "argocd.test:8080"
    
    # Mock socket to simulate ArgoCD available
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('socket.socket') as mock_socket:
        
        # Socket connection successful
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        mock_socket_instance.connect_ex.return_value = 0  # Success
        
        result = await health_check()
        
        assert result["services"]["argo_cd"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_argocd_dev_mode_connection_failed():
    """Test health check for ArgoCD in development mode with connection failure."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "development"
    mock_settings.verify_ssl = False
    mock_settings.argo_cd_url = "argocd.test"
    
    # Mock socket to simulate ArgoCD not available
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('socket.socket') as mock_socket:
        
        # Socket connection failed
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        mock_socket_instance.connect_ex.return_value = 1  # Failure
        
        result = await health_check()
        
        assert result["services"]["argo_cd"]["status"] == "unhealthy"
        assert "optional" in result["services"]["argo_cd"]["error"]

@pytest.mark.asyncio
async def test_health_check_argocd_dev_mode_socket_error():
    """Test health check for ArgoCD in development mode with socket error."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "development"
    mock_settings.verify_ssl = False
    mock_settings.argo_cd_url = "argocd.test:invalid"  # Invalid URL format
    
    # Mock socket to simulate ArgoCD socket error
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('socket.socket') as mock_socket:
        
        # Socket raises exception
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance
        mock_socket_instance.connect_ex.side_effect = Exception("Invalid address format")
        
        result = await health_check()
        
        assert result["services"]["argo_cd"]["status"] == "unhealthy"
        assert "error in development" in result["services"]["argo_cd"]["error"]

@pytest.mark.asyncio
async def test_health_check_argocd_prod_mode():
    """Test health check for ArgoCD in production mode."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "production"
    mock_settings.verify_ssl = False
    mock_settings.argo_cd_url = "http://argocd.test"
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.__aenter__.return_value.get.return_value = mock_response
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        result = await health_check()
        
        assert result["services"]["argo_cd"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_argocd_prod_mode_auth_required():
    """Test health check for ArgoCD in production mode with auth required."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "production"
    mock_settings.verify_ssl = False
    mock_settings.argo_cd_url = "http://argocd.test"
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 401  # Auth required
    mock_client.__aenter__.return_value.get.return_value = mock_response
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        result = await health_check()
        
        # 401 is acceptable for ArgoCD
        assert result["services"]["argo_cd"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_argocd_prod_mode_error():
    """Test health check for ArgoCD in production mode with error."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "production"
    mock_settings.verify_ssl = False
    mock_settings.argo_cd_url = "http://argocd.test"
    
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal server error"
    mock_client.__aenter__.return_value.get.return_value = mock_response
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        result = await health_check()
        
        assert result["status"] == "degraded"
        assert result["services"]["argo_cd"]["status"] == "unhealthy"
        assert "500" in result["services"]["argo_cd"]["error"]

@pytest.mark.asyncio
async def test_health_check_argocd_prod_mode_connection_error():
    """Test health check for ArgoCD in production mode with connection error."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.environment = "production"
    mock_settings.verify_ssl = False
    mock_settings.argo_cd_url = "http://argocd.test"
    
    # Mock client for kubernetes succeeds
    mock_client_k8s = AsyncMock()
    mock_response_k8s = MagicMock()
    mock_response_k8s.status_code = 200
    
    # Mock client for ArgoCD fails
    mock_client_argo = AsyncMock()
    mock_client_argo.__aenter__.return_value.get.side_effect = Exception("Connection error")
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', side_effect=[mock_client_k8s, mock_client_argo]):
        
        # Mock the first client call (kubernetes) to succeed
        mock_client_k8s.__aenter__.return_value.get.return_value = mock_response_k8s
        
        result = await health_check()
        
        assert result["status"] == "degraded"
        assert result["services"]["argo_cd"]["status"] == "unhealthy"
        assert "Connection error" in result["services"]["argo_cd"]["error"]
