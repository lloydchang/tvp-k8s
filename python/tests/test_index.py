import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

# Ensure api directory is in path
api_dir = str(Path(__file__).parent.parent.parent)
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

def test_root_endpoint(test_client):
    """Test that the root endpoint returns the correct data structure."""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert "endpoints" in data
    assert isinstance(data["endpoints"], list)

def test_health_check_all_healthy(test_client, mock_kubernetes_client, mock_argo_cd_token):
    """Test that health check returns healthy when all services are healthy."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["kubernetes"]["status"] == "healthy"
    assert data["services"]["argo_cd"]["status"] == "healthy"

def test_health_check_kubernetes_unhealthy(test_health_check_kubernetes_unhealthy):
    """Test health check when Kubernetes is unhealthy."""
    response = test_health_check_kubernetes_unhealthy.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["kubernetes"]["status"] == "unhealthy"
    assert "error" in data["services"]["kubernetes"]
    assert data["services"]["argo_cd"]["status"] == "healthy"  # Argo CD still healthy

def test_health_check_argo_cd_unhealthy(test_health_check_argo_cd_unhealthy):
    """Test health check when Argo CD is unhealthy."""
    response = test_health_check_argo_cd_unhealthy.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["argo_cd"]["status"] == "unhealthy"
    assert "error" in data["services"]["argo_cd"]
    assert data["services"]["kubernetes"]["status"] == "healthy"  # Kubernetes still healthy

def test_lifespan():
    """Test that the lifespan context manager starts the reconciliation thread."""
    from api.index import lifespan
    import asyncio
    
    # Create a mock app
    mock_app = MagicMock()
    
    # Create the actual context manager
    cm = lifespan(mock_app)
    
    # Run the async context manager in an event loop
    with patch("api.index.start_reconciliation_thread") as mock_start_thread:
        async def test():
            async with cm as result:
                pass
            return result
        
        asyncio.run(test())
        
        # Verify the thread was started
        mock_start_thread.assert_called_once()

def test_lifespan_error_handling():
    """Test that the lifespan context manager handles errors when starting the reconciliation thread."""
    from api.index import lifespan
    import asyncio
    
    # Create a mock app
    mock_app = MagicMock()
    
    # Create the actual context manager
    cm = lifespan(mock_app)
    
    # Run the async context manager in an event loop
    with patch("api.index.start_reconciliation_thread") as mock_start_thread:
        mock_start_thread.side_effect = Exception("Test exception")
        
        async def test():
            async with cm as result:
                pass
            return result
        
        # Should not raise an exception
        asyncio.run(test())
        
        # Verify the thread was started
        mock_start_thread.assert_called_once()

def test_router_prefixes(test_client):
    """Test that router prefixes are correctly configured."""
    # Check that the routes are configured correctly
    response = test_client.get("/")
    assert response.status_code == 200
    
    # For proxy endpoints, we can't easily mock them, so let's check that they
    # at least exist by verifying the router is configured, rather than testing 
    # the actual response which may be 500 in tests due to missing backend services
    # We'll do this by checking the app routes directly
    from api.index import app
    
    router_paths = [route.path for route in app.routes if hasattr(route, "path")]
    
    # Check that kubernetes, argo/cd and gitops routes exist
    assert any(path.startswith("/kubernetes/") for path in router_paths)
    assert any(path.startswith("/argo/cd/") for path in router_paths)
    assert any(path.startswith("/gitops") for path in router_paths)

def test_cors_configuration():
    """Test that CORS middleware is configured correctly."""
    from api.index import app
    from starlette.middleware.cors import CORSMiddleware
    
    # Check that CORS middleware is included
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            break
    
    assert cors_middleware is not None
    # FastAPI middleware doesn't expose options directly
    # Instead check that CORS middleware is properly configured by inspecting responses

def test_cors_error_handling(test_client):
    """Test CORS handling in error cases."""
    # Test with an option request
    headers = {
        "Origin": "http://example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization"
    }
    response = test_client.options("/", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    # Accept either the specific origin or wildcard
    assert response.headers["access-control-allow-origin"] in ["http://example.com", "*"]

def test_argo_cd_token_null_response(test_client):
    """Test handling of null token response from Argo CD"""
    with patch("api.index.get_argo_cd_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = None  # Return None to simulate null token
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["argo_cd"]["status"] == "unhealthy"

def test_uvicorn_main():
    """Test that the main function configures uvicorn correctly."""
    with patch("uvicorn.run") as mock_run:
        from api.index import main
        main()
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0]
        assert call_args[0] == "api.index:app"
        assert "host" in mock_run.call_args[1]
        assert "port" in mock_run.call_args[1]

def test_startup_reconciliation():
    """Test that reconciliation is started at application startup."""
    from api.index import lifespan
    import asyncio
    
    # Create a mock app
    mock_app = MagicMock()
    
    # Create the actual context manager
    cm = lifespan(mock_app)
    
    # Run the async context manager in an event loop
    with patch("api.index.start_reconciliation_thread") as mock_start_thread:
        async def test():
            async with cm as result:
                pass
            return result
        
        asyncio.run(test())
        
        # Verify the thread was started
        mock_start_thread.assert_called_once()

def test_cors_headers(test_client):
    """Test that CORS headers are correctly added to responses."""
    headers = {"Origin": "http://example.com"}
    response = test_client.get("/", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"

def test_router_configuration():
    """Test that all routers are correctly included in the app."""
    from api.index import app
    
    # Check router prefixes by examining the routes
    router_prefixes = set()
    for route in app.routes:
        if hasattr(route, "path"):
            router_prefixes.add(route.path.split("/")[1] if len(route.path.split("/")) > 1 else "")
    
    # Check that all expected router prefixes are present
    expected_prefixes = {"", "kubernetes", "argo", "gitops"}
    for prefix in expected_prefixes:
        assert prefix in router_prefixes or any(p.startswith(prefix) for p in router_prefixes)

def test_main_function():
    """Test that the main function correctly sets up uvicorn with the app."""
    with patch("uvicorn.run") as mock_run:
        from api.index import main
        main()
        
        # Verify uvicorn is configured correctly
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0] == "api.index:app"
        assert mock_run.call_args[1]["host"] == "0.0.0.0"
        assert mock_run.call_args[1]["port"] == 8000
        assert mock_run.call_args[1]["reload"] is True

@pytest.mark.asyncio
async def test_health_check_partial_degradation(test_client):
    """Test health check when some services are degraded"""
    # Mock Kubernetes healthy but Argo CD unhealthy
    with patch("api.index.get_kubernetes_client") as mock_k8s, \
         patch("api.index.get_argo_cd_token", new_callable=AsyncMock) as mock_argo:
        
        # Configure Kubernetes as healthy
        k8s_client = MagicMock()
        namespace_list = MagicMock()
        namespace_list.items = [MagicMock()]
        k8s_client.list_namespace = MagicMock(return_value=namespace_list)
        mock_k8s.return_value = k8s_client
        
        # Configure Argo CD as unhealthy
        mock_argo.side_effect = Exception("Argo CD connection error")
        
        # Make the request
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Verify partial degradation
        assert data["status"] == "degraded"
        assert data["services"]["kubernetes"]["status"] == "healthy"
        assert data["services"]["argo_cd"]["status"] == "unhealthy"
        assert "error" in data["services"]["argo_cd"]

def test_health_check_null_token(test_client):
    """Test health check when Argo CD returns null token"""
    with patch("api.index.get_argo_cd_token", new_callable=AsyncMock) as mock_token:
        mock_token.return_value = None
        
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["services"]["argo_cd"]["status"] == "unhealthy"
        assert "error" in data["services"]["argo_cd"]
        assert "Failed to obtain Argo CD token" in data["services"]["argo_cd"]["error"]

def test_health_check_complex_scenarios(test_client):
    """Test health check with complex failure scenarios"""
    with patch("api.index.get_kubernetes_client") as mock_k8s, \
         patch("api.index.get_argo_cd_token", new_callable=AsyncMock) as mock_argo:
        
        # Test when both services time out
        mock_k8s.side_effect = TimeoutError("Kubernetes API timeout")
        mock_argo.side_effect = TimeoutError("Argo CD API timeout")
        
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["services"]["kubernetes"]["status"] == "unhealthy"
        assert data["services"]["argo_cd"]["status"] == "unhealthy"

def test_sys_path_modification():
    """Test that the sys.path is correctly modified to include the necessary directories."""
    # This is indirectly tested by checking that imports work correctly
    from api.index import app
    assert app is not None
    
    from python.app.gitops import proxy as gitops_router
    assert gitops_router is not None
    
    from python.app.argo_cd_api import proxy as argo_cd_proxy
    assert argo_cd_proxy is not None
    
    from python.app.kubernetes_api import proxy as kubernetes_proxy
    assert kubernetes_proxy is not None

def test_app_initialization():
    """Test that the FastAPI app is initialized with the correct parameters."""
    from api.index import app
    
    assert app.title == "TVP API"
    assert app.version == "1.0.0"
    # Check for lifespan in a compatible way with FastAPI implementations
    assert app.router.lifespan_context is not None

def test_router_prefix_conflicts(test_client):
    """Test that there are no router prefix conflicts."""
    # Get all routes from the app
    from api.index import app
    
    # Extract route paths
    route_paths = [route.path for route in app.routes if hasattr(route, "path")]
    
    # Check there are no duplicate paths
    assert len(route_paths) == len(set(route_paths)), "Duplicate route paths found"

def test_startup_dependency_failure():
    """Test handling of dependency failures during app startup."""
    from api.index import lifespan
    import asyncio
    
    # Create a mock app
    mock_app = MagicMock()
    
    # Create the actual context manager
    cm = lifespan(mock_app)
    
    # Run the async context manager in an event loop
    with patch("api.index.start_reconciliation_thread") as mock_start_thread:
        mock_start_thread.side_effect = Exception("Failed to start")
        
        async def test():
            async with cm as result:
                pass
            return result
        
        # Should not propagate the exception
        asyncio.run(test())

def test_endpoint_error_propagation(test_client):
    """Test that endpoint errors are properly propagated"""
    # Test root endpoint with failing dependencies
    with patch("api.index.get_settings") as mock_settings:
        mock_settings.side_effect = Exception("Config error")
        try:
            response = test_client.get("/health") # Test /health as it uses get_settings
            assert response.status_code == 500
        except Exception as e:
            # Either way, the request should not succeed
            assert "Config error" in str(e)

def test_health_check_timeout_scenarios(test_client):
    """Test health check with timeout scenarios"""
    with patch("api.index.get_kubernetes_client") as mock_k8s, \
         patch("api.index.get_argo_cd_token", new_callable=AsyncMock) as mock_argo:
        
        # Configure Kubernetes to time out
        mock_k8s.side_effect = TimeoutError("Kubernetes API timeout")
        
        # Configure Argo CD to time out
        mock_argo.side_effect = TimeoutError("Argo CD API timeout")
        
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["services"]["kubernetes"]["status"] == "unhealthy"
        assert data["services"]["argo_cd"]["status"] == "unhealthy"