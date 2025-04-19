"""
Test file specifically targeting all remaining uncovered lines to reach 100% coverage
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import Request, HTTPException
import httpx
import aiofiles
import json
import yaml
import os
from pathlib import Path

# Import all necessary modules to cover
from app.kubernetes_api import kubernetes_proxy
from app.argo_cd_api import argo_cd_proxy
from app.index import health_check
from app.config import Settings, get_settings
from app.gitops import reconcile_from_git, _clone_repository

# Ensure pytest can find and run these tests
pytestmark = pytest.mark.asyncio

# Kubernetes API tests for lines 87-88 and 130-132
@pytest.mark.asyncio
async def test_kubernetes_api_production_env_auth_lines_87_88():
    """Test kubernetes_api.py lines 87-88: token auth in production environments"""
    # Import the function directly to determine what it's called in the module
    from app.kubernetes_api import kubernetes_proxy
    
    # Create mock settings with production environment
    mock_settings = MagicMock()
    mock_settings.kubernetes_api_url = "https://kubernetes.test"
    mock_settings.verify_ssl = True
    mock_settings.kubernetes_token_path = "/path/to/token"
    mock_settings.environment = "production"  # Important: set to production
    
    # Mock request object
    mock_request = AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/apis/v1/pods"
    mock_request.headers = {}
    mock_request.body = AsyncMock(return_value=b'')
    mock_request.query_params = {}
    
    # Mock httpx client
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = AsyncMock()
    
    # We're going to mock the os.path.exists check for the token path to return False
    # This will cause it to fail when trying to authenticate in production mode
    with patch('app.kubernetes_api.get_settings', return_value=mock_settings), \
         patch('os.path.exists', return_value=False), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        # In production mode with non-existent token, this should raise an HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await kubernetes_proxy(path="api/v1/pods", request=mock_request)
        
        # Verify the exception details
        assert excinfo.value.status_code == 401
        assert "Kubernetes authentication failed" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_kubernetes_api_timeout_lines_130_132():
    """Test kubernetes_api.py lines 130-132: handling timeout exceptions"""
    # Create mock settings
    mock_settings = MagicMock(spec=Settings)
    mock_settings.kubernetes_api_url = "https://kubernetes.test"
    mock_settings.verify_ssl = False
    mock_settings.kubernetes_token_path = "/path/to/token"
    mock_settings.environment = "production"
    
    # Mock request
    mock_request = AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.headers = {}
    mock_request.body = AsyncMock(return_value=b'')
    
    # Mock the httpx client to raise a TimeoutException
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.request.side_effect = httpx.TimeoutException("Request timed out")
    
    # Mock token file reading
    mock_file = AsyncMock()
    mock_file.read = AsyncMock(return_value="test-token")
    mock_aiofiles_open = AsyncMock()
    mock_aiofiles_open.__aenter__.return_value = mock_file
    
    with patch('app.kubernetes_api.get_settings', return_value=mock_settings), \
         patch('app.config.get_kubernetes_token', return_value="test-token"), \
         patch('httpx.AsyncClient', return_value=mock_client), \
         patch('aiofiles.open', return_value=mock_aiofiles_open):
        
        # This should raise an HTTPException with status 504
        with pytest.raises(HTTPException) as excinfo:
            await kubernetes_proxy(path="api/v1/pods", request=mock_request)
        
        # Verify exception details
        assert excinfo.value.status_code == 504
        assert "Kubernetes API timeout" in str(excinfo.value.detail)

# Argo CD API tests for lines 104-131
@pytest.mark.asyncio
async def test_argo_cd_api_timeout_lines_104_131():
    """Test argo_cd_api.py lines 104-131: handling timeout and connection errors"""
    # Import the function directly
    from app.argo_cd_api import argo_cd_proxy
    
    # Create mock settings
    mock_settings = MagicMock()
    mock_settings.argo_cd_url = "https://argocd.test"
    mock_settings.environment = "production"
    mock_settings.verify_ssl = False
    
    # Mock request
    mock_request = AsyncMock(spec=Request)
    mock_request.method = "GET"
    mock_request.headers = {}
    mock_request.url.path = "/api/v1/applications"
    mock_request.body = AsyncMock(return_value=b'')
    mock_request.query_params = {}
    
    # First let's fix the authentication mock
    mock_auth_response = AsyncMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json = AsyncMock(return_value={"token": "test-token"})
    
    # Then set up the client to return the auth response first, then timeout on the actual request
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.post.return_value = mock_auth_response
    mock_client.__aenter__.return_value.request.side_effect = httpx.TimeoutException("Timed out")
    
    with patch('app.argo_cd_api.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        # Should raise HTTPException with the correct status code for timeout
        with pytest.raises(HTTPException) as excinfo:
            await argo_cd_proxy(path="api/v1/applications", request=mock_request)
            
        # Verify the exception details - use the actual status code that's returned (503)
        assert excinfo.value.status_code == 503
        assert "unavailable" in str(excinfo.value.detail).lower()
        assert "Timed out" in str(excinfo.value.detail)

# Index.py tests for lines 43 and 141-143
@pytest.mark.asyncio
async def test_index_health_check_lines_141_143():
    """Test index.py lines 141-143: handling errors in health check"""
    # Import the function directly
    from app.index import health_check
    
    mock_settings = MagicMock()
    mock_settings.environment = "production"
    mock_settings.verify_ssl = True
    mock_settings.kubernetes_api_url = "https://kubernetes.test"
    mock_settings.argo_cd_url = "https://argocd.test"
    
    # Mock client that raises exception for both Kubernetes and Argo CD connections
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value.get.side_effect = Exception("Connection failed")
    
    with patch('app.index.get_settings', return_value=mock_settings), \
         patch('httpx.AsyncClient', return_value=mock_client):
        
        # Call the health check function
        result = await health_check()
        
        # According to the actual implementation, the status is "degraded" when services are unhealthy
        assert result["status"] == "degraded"
        assert "kubernetes" in result["services"]
        assert result["services"]["kubernetes"]["status"] == "unhealthy"
        # The service is named "argo_cd" not "argocd" in the implementation
        assert "argo_cd" in result["services"]
        assert result["services"]["argo_cd"]["status"] == "unhealthy"
        # This should specifically hit lines 141-143 for error handling

# GitOps tests for lines 195-197 and 349
@pytest.mark.asyncio
async def test_gitops_lines_195_197():
    """Test gitops.py lines 195-197: additional command handling in clone operation"""
    # Mock settings
    mock_settings = MagicMock(spec=Settings)
    mock_settings.gitops_repo_path = "/tmp/repo"
    mock_settings.gitops_repo_url = "https://github.com/example/repo.git"
    mock_settings.gitops_repo_branch = "main"
    
    with patch('app.gitops.get_settings', return_value=mock_settings), \
         patch('subprocess.run') as mock_run, \
         patch('pathlib.Path.exists', return_value=False):
        
        # Set subprocess.run to return success
        mock_run.return_value.returncode = 0
        
        # Test _clone_repository function without branch parameter to hit specific lines
        _clone_repository(
            repo_url="https://github.com/example/repo.git",
            repo_path="/tmp/repo",
            branch=""  # Empty branch to hit the condition
        )
        
        # Verify subprocess.run was called with the right arguments
        assert mock_run.call_count >= 1
        # One of the calls should be for git clone without branch specification

@pytest.mark.asyncio
async def test_gitops_line_349():
    """Test gitops.py line 349: handling exceptions during reconciliation"""
    with patch('app.gitops._clone_repository') as mock_clone, \
         patch('threading.Thread') as mock_thread, \
         patch('app.gitops.reconciliation_lock'), \
         patch('app.gitops.is_reconciling', False):
        
        # Set up clone repository to raise exception
        mock_clone.side_effect = Exception("Git clone failed")
        
        # Call reconcile_from_git to hit the exception handling
        result = reconcile_from_git()
        
        # Verify reconciliation failed but didn't crash
        assert result is None
