"""
Test the main module functionality in api/index.py
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Ensure the API directory is in the path
api_path = str(Path(__file__).parent.parent.parent)
if api_path not in sys.path:
    sys.path.insert(0, api_path)

from api.index import app, lifespan, health_check, root, main

"""
Module for API index tests to ensure they properly import from the correct location.
"""
from .test_index import *

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

def test_main_function():
    """Test the main function in api/index.py that runs the uvicorn server."""
    with patch("uvicorn.run") as mock_run:
        main()
        mock_run.assert_called_once_with(
            "api.index:app",
            host="0.0.0.0", 
            port=8000,
            reload=True
        )

def test_app_structure():
    """Test the application structure is properly configured."""
    # Check FastAPI app configuration
    assert app.title == "TVP API"
    assert app.version == "1.0.0"
    
    # Check that middleware is configured
    from fastapi.middleware.cors import CORSMiddleware
    cors_middleware_found = False
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware_found = True
            break
    assert cors_middleware_found, "CORS middleware should be configured"
    
    # Check router prefixes are properly set up
    router_prefixes = []
    for route in app.routes:
        if hasattr(route, "path"):
            router_prefixes.append(route.path.split("/")[1] if route.path != "/" else "root")
    
    # Ensure all expected router prefixes are included
    assert "deploy" in router_prefixes, "Deploy router should be mounted"
    assert "reconcile" in router_prefixes, "Reconcile router should be mounted"
    assert "argo" in router_prefixes, "Argo CD router should be mounted"
    assert "kubernetes" in router_prefixes, "Kubernetes router should be mounted"
    assert "health" in router_prefixes, "Health endpoint should exist"
    assert "root" in router_prefixes, "Root endpoint should exist"

def test_health_check_endpoint():
    """Test the health check endpoint functionality."""
    # Create test client
    client = TestClient(app)
    
    # Patch dependencies
    with patch("api.index.get_kubernetes_client") as mock_k8s_client, \
         patch("api.index.get_argo_cd_token") as mock_token:
        
        # Configure mocks for successful response
        k8s_client_mock = MagicMock()
        namespace_list = MagicMock()
        namespace_list.items = [MagicMock()]
        k8s_client_mock.list_namespace = MagicMock(return_value=namespace_list)
        mock_k8s_client.return_value = k8s_client_mock
        
        # Mock token return with async mock
        mock_async = AsyncMock()
        mock_async.return_value = "test-token"
        mock_token.side_effect = mock_async
        
        # Test health endpoint with successful response
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["kubernetes"]["status"] == "healthy"
        assert data["services"]["argo_cd"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_lifespan_function():
    """Test the lifespan context manager function."""
    mock_app = MagicMock()
    with patch("api.index.start_reconciliation_thread") as mock_start:
        async with lifespan(mock_app):
            pass
        # Assert the reconciliation thread was started
        mock_start.assert_called_once()

@pytest.mark.asyncio
async def test_lifespan_exception_handling():
    """Test the lifespan context manager handles exceptions."""
    mock_app = MagicMock()
    with patch("api.index.start_reconciliation_thread") as mock_start:
        mock_start.side_effect = Exception("Test exception")
        # The exception should be caught and not propagated
        async with lifespan(mock_app):
            pass
        # Assert the reconciliation thread was attempted to be started
        mock_start.assert_called_once()

def test_root_endpoint():
    """Test the root endpoint."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TVP API"
    assert data["version"] == "1.0.0"
    assert data["status"] == "healthy"
    assert "endpoints" in data
    assert isinstance(data["endpoints"], list)
    assert len(data["endpoints"]) > 0

def test_health_check_kubernetes_error():
    """Test health check when Kubernetes has an error."""
    client = TestClient(app)
    with patch("api.index.get_kubernetes_client") as mock_k8s_client, \
         patch("api.index.get_argo_cd_token") as mock_token:
        
        # Configure Kubernetes mock to raise an exception
        mock_k8s_client.side_effect = Exception("Kubernetes error")
        
        # Configure Argo CD mock to return successfully
        mock_async = AsyncMock()
        mock_async.return_value = "test-token"
        mock_token.side_effect = mock_async
        
        # Test health endpoint with Kubernetes error
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["kubernetes"]["status"] == "unhealthy"
        assert "error" in data["services"]["kubernetes"]
        assert data["services"]["argo_cd"]["status"] == "healthy"

def test_health_check_argocd_error():
    """Test health check when Argo CD has an error."""
    client = TestClient(app)
    with patch("api.index.get_kubernetes_client") as mock_k8s_client, \
         patch("api.index.get_argo_cd_token") as mock_token:
        
        # Configure Kubernetes mock to return successfully
        k8s_client_mock = MagicMock()
        namespace_list = MagicMock()
        namespace_list.items = [MagicMock()]
        k8s_client_mock.list_namespace = MagicMock(return_value=namespace_list)
        mock_k8s_client.return_value = k8s_client_mock
        
        # Configure Argo CD mock to raise an exception
        mock_async = AsyncMock()
        mock_async.side_effect = Exception("Argo CD error")
        mock_token.side_effect = mock_async
        
        # Test health endpoint with Argo CD error
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["kubernetes"]["status"] == "healthy"
        assert data["services"]["argo_cd"]["status"] == "unhealthy"
        assert "error" in data["services"]["argo_cd"]

def test_health_check_argocd_null_token():
    """Test health check when Argo CD returns a null token."""
    client = TestClient(app)
    with patch("api.index.get_kubernetes_client") as mock_k8s_client, \
         patch("api.index.get_argo_cd_token") as mock_token:
        
        # Configure Kubernetes mock to return successfully
        k8s_client_mock = MagicMock()
        namespace_list = MagicMock()
        namespace_list.items = [MagicMock()]
        k8s_client_mock.list_namespace = MagicMock(return_value=namespace_list)
        mock_k8s_client.return_value = k8s_client_mock
        
        # Configure Argo CD mock to return null token
        mock_async = AsyncMock()
        mock_async.return_value = None
        mock_token.side_effect = mock_async
        
        # Test health endpoint with null Argo CD token
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["kubernetes"]["status"] == "healthy"
        assert data["services"]["argo_cd"]["status"] == "unhealthy"
        assert "error" in data["services"]["argo_cd"]
        assert "Failed to obtain Argo CD token" in data["services"]["argo_cd"]["error"]

def test_health_check_both_errors():
    """Test health check when both Kubernetes and Argo CD have errors."""
    client = TestClient(app)
    with patch("api.index.get_kubernetes_client") as mock_k8s_client, \
         patch("api.index.get_argo_cd_token") as mock_token:
        
        # Configure Kubernetes mock to raise an exception
        mock_k8s_client.side_effect = Exception("Kubernetes error")
        
        # Configure Argo CD mock to raise an exception
        mock_async = AsyncMock()
        mock_async.side_effect = Exception("Argo CD error")
        mock_token.side_effect = mock_async
        
        # Test health endpoint with both services having errors
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["kubernetes"]["status"] == "unhealthy"
        assert "error" in data["services"]["kubernetes"]
        assert data["services"]["argo_cd"]["status"] == "unhealthy"
        assert "error" in data["services"]["argo_cd"]

def test_routers_included():
    """Test that all expected routers are included in the app."""
    # Extract all routes from the app
    routes = [route.path for route in app.routes]
    
    # Check for expected route prefixes
    deploy_routes = [r for r in routes if r.startswith("/deploy")]
    reconcile_routes = [r for r in routes if r.startswith("/reconcile")]
    argo_routes = [r for r in routes if r.startswith("/argo/cd")]
    kubernetes_routes = [r for r in routes if r.startswith("/kubernetes")]
    
    # Assert we have routes for each prefix
    assert len(deploy_routes) > 0, "No deploy routes found"
    assert len(reconcile_routes) > 0, "No reconcile routes found"
    assert len(argo_routes) > 0, "No Argo CD routes found"
    assert len(kubernetes_routes) > 0, "No Kubernetes routes found"
    
    # Check for the health and root endpoints
    assert "/" in routes, "Root endpoint not found"
    assert "/health" in routes, "Health endpoint not found"

def test_cors_configuration():
    """Test CORS middleware configuration."""
    # Extract CORS middleware from the app
    from fastapi.middleware.cors import CORSMiddleware
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            break
    
    assert cors_middleware is not None, "CORS middleware not found"
    
    # Check CORS settings - access kwargs instead of options
    assert cors_middleware.kwargs.get("allow_origins") == ["*"], "CORS allow_origins should be ['*']"
    assert cors_middleware.kwargs.get("allow_credentials") is True, "CORS allow_credentials should be True"
    assert cors_middleware.kwargs.get("allow_methods") == ["*"], "CORS allow_methods should be ['*']"
    assert cors_middleware.kwargs.get("allow_headers") == ["*"], "CORS allow_headers should be ['*']"