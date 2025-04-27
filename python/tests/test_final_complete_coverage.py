"""Test module for achieving complete 100% test coverage"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
import socket
import asyncio
from fastapi import HTTPException, BackgroundTasks
from fastapi.testclient import TestClient

# Import modules that need additional test coverage
from python.app.argo_cd_api import get_argo_cd_token, get_argo_cd_auth_token, argo_cd_proxy
from python.app.gitops import deploy_microservices, get_gitops_status
from python.app.index import health_check, root
from python.app.kubernetes_api import kubernetes_proxy

@pytest.mark.asyncio
async def test_argo_cd_proxy_non_json_response():
    """Test argo_cd_proxy with a response that raises an exception during JSON parsing."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.get_argo_cd_auth_token') as mock_token, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
        mock_settings.return_value.verify_ssl = True
        
        # Configure auth token
        mock_token.return_value = "test-token"
        
        # Configure mock request
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers = {}
        
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock response that raises an exception during JSON parsing
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "Non-JSON response"
        mock_response.json.side_effect = ValueError("Invalid JSON format")
        mock_client_instance.request.return_value = mock_response
        
        # Call the function
        result = await argo_cd_proxy("applications", mock_request)
        
        # Verify the fallback to raw response
        assert result["status_code"] == 200
        assert result["content"] == "Non-JSON response"

@pytest.mark.asyncio
async def test_argo_cd_proxy_additional_development_paths():
    """Test argo_cd_proxy in development mode with different paths."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.get_argo_cd_auth_token') as mock_token:
        
        # Configure settings for development mode
        mock_settings.return_value.environment = "development"
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
        
        # Mock the auth token
        mock_token.return_value = "mock-dev-token"
        
        # Test applications path which has specific mock data
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.body = AsyncMock(return_value=b'')
        
        result = await argo_cd_proxy("applications", mock_request)
        
        # Verify that mock data is returned for applications
        assert "items" in result
        assert result["items"][0]["metadata"]["name"] == "example-app"

@pytest.mark.asyncio
async def test_health_check_url_parsing():
    """Test health_check with different URL formats to cover lines 141-143 in index.py."""
    with patch('python.app.index.get_settings') as mock_settings, \
         patch('python.app.index.check_kubernetes_health') as mock_k8s_health, \
         patch('python.app.index.check_argo_cd_health') as mock_argocd_health:

        # Configure mock for development mode
        mock_settings.return_value = MagicMock()
        mock_settings.return_value.environment = "development"
        mock_settings.return_value.kubernetes_api_url = "https://kubernetes.default.svc"
        mock_settings.return_value.argo_cd_server_url = "https://argocd.example.com"
        
        # Pre-define return values for health checks to avoid actual operations
        mock_k8s_health.return_value = {"status": "healthy", "message": "Connected"}
        mock_argocd_health.return_value = {"status": "healthy", "message": "Connected"}
        
        # Test with direct call to health_check function (safer than using client)
        from python.app.index import health_check
        
        # Test with default URL
        result = await health_check()
        assert result["status"] == "healthy"
        assert result["services"]["kubernetes"]["status"] == "healthy"
        assert result["services"]["argo_cd"]["status"] == "healthy"
        
        # Test with different URL formats for ArgoCD
        urls_to_test = [
            "argocd.example.com",                # No protocol
            "http://argocd.example.com",         # HTTP protocol
            "https://argocd.example.com",        # HTTPS protocol
            "http://argocd.example.com:8080",    # With port
            "argocd.example.com:443"             # No protocol but with port
        ]
        
        # Test each URL format
        for url in urls_to_test:
            mock_settings.return_value.argo_cd_server_url = url
            result = await health_check()
            assert result["status"] == "healthy"
            assert result["services"]["argo_cd"]["status"] == "healthy"

def test_deploy_microservices_background_task():
    """Test deploy_microservices properly adds tasks to background tasks."""
    from python.app.gitops import deploy_microservices, DeploymentRequest
    from fastapi import BackgroundTasks
    import asyncio
    
    # Create a mock for the BackgroundTasks
    mock_background_tasks = MagicMock(spec=BackgroundTasks)
    
    # Setup other necessary mocks
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.mkdir") as mock_mkdir, \
         patch("builtins.open", MagicMock()), \
         patch("yaml.safe_load") as mock_yaml_load, \
         patch("yaml.safe_dump") as mock_yaml_dump, \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.reconcile_from_git") as mock_reconcile_func:
        
        # Configure mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"image": "old-image:v1"}
        
        # Create deployment request
        deployment_req = DeploymentRequest(
            image="test-image:latest",
            replicas=2
        )
        
        # Run the function
        result = asyncio.run(deploy_microservices(
            "test-namespace", 
            "test-app", 
            deployment_req, 
            mock_background_tasks
        ))
        
        # Verify background task was added
        mock_background_tasks.add_task.assert_called_once_with(mock_reconcile_func)
        
        # Verify response
        assert result["status"] == "deployment_triggered"

def test_kubernetes_api_timeouts_direct():
    """Test the Kubernetes API proxy with direct timeout simulation."""
    from python.app.kubernetes_api import proxy as kubernetes_proxy
    import httpx
    import asyncio
    
    # Create a mock request
    mock_request = MagicMock()
    mock_request.url.path = "api/v1/namespaces"
    
    # Mock the settings and token
    with patch('python.app.kubernetes_api.get_settings') as mock_settings, \
         patch('python.app.kubernetes_api.get_kubernetes_token') as mock_token, \
         patch('httpx.AsyncClient.request') as mock_request_func:
        
        # Configure mocks
        mock_config = MagicMock()
        mock_config.kubernetes_api_url = "https://kube.example.com"
        mock_settings.return_value = mock_config
        
        mock_token.return_value = "fake-token"
        
        # Simulate a timeout with httpx.TimeoutException
        mock_request_func.side_effect = httpx.TimeoutException("Connection timed out")
        
        # Use asyncio.run to properly await the async function
        response = asyncio.run(kubernetes_proxy(mock_request))
        
        # Verify the response
        assert response.status_code == 504
        assert "timeout" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_get_gitops_status_complete():
    """Test get_gitops_status to cover line 349 in gitops.py."""
    with patch('python.app.gitops.proxy.get') as mock_get:
        # Mock the proxy router get method
        mock_get.return_value = {
            "service": "TVP GitOps API",
            "description": "GitOps operations for continuous delivery",
            "available_endpoints": {
                "deploy": "/api/gitops/deploy/{namespace}/{microservices_name}",
                "reconcile": "/api/gitops/reconcile",
                "status": "/api/gitops/status/deploy/{namespace}/{microservices_name}"
            }
        }
        
        # This is an async coroutine that returns a GitOpsStatus object
        result = await get_gitops_status()
    
        # Verify structure of response
        assert hasattr(result, "status")
        assert hasattr(result, "microservices")

def test_kubernetes_api_timeouts_mock():
    """Test the Kubernetes API proxy timeout handling with mocks."""
    from python.app.kubernetes_api import proxy as kubernetes_proxy
    import httpx
    import asyncio
    
    # Mock the request
    mock_request = MagicMock()
    mock_request.url.path = "api/v1/namespaces"
    
    # Mock the get_settings function
    with patch('python.app.kubernetes_api.get_settings') as mock_settings, \
         patch('python.app.kubernetes_api.get_kubernetes_token') as mock_token, \
         patch('httpx.AsyncClient.request') as mock_request_func:
        
        # Configure mocks
        mock_config = MagicMock()
        mock_config.kubernetes_api_url = "https://kube.example.com"
        mock_settings.return_value = mock_config
        
        mock_token.return_value = "fake-token"
        
        # Simulate a timeout
        mock_request_func.side_effect = httpx.TimeoutException("Connection timed out")
        
        # Use asyncio.run to properly await the async function
        response = asyncio.run(kubernetes_proxy("api/v1/namespaces", mock_request))
        
        # Assert that we got an error response
        assert response.status_code == 504
        assert "timeout" in response.json()["detail"].lower()

def test_kubernetes_api_auth_headers_direct():
    """Test kubernetes API auth headers to cover lines 87-88 in kubernetes_api.py."""
    with patch('python.app.kubernetes_api.get_kubernetes_token') as mock_token:
        
        # Setup mock to return a token
        mock_token.return_value = "test-k8s-token"
        
        # Import the relevant function
        from python.app.kubernetes_api import _prepare_request_headers
        
        # Test with default headers (no auth header in request)
        request_headers = {"Content-Type": "application/json"}
        headers = _prepare_request_headers(request_headers)
        
        # Verify authorization header was added
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-k8s-token"
        
        # Test with existing auth header in request
        request_headers = {"Authorization": "Bearer custom-token"}
        headers = _prepare_request_headers(request_headers)
        
        # Verify authorization header was preserved
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer custom-token"
        
        # Test with no token available
        mock_token.return_value = None
        headers = _prepare_request_headers({})
        
        # Verify no authorization header is added
        assert "Authorization" not in headers
