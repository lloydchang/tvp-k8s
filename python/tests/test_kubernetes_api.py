from unittest.mock import patch, MagicMock, mock_open, AsyncMock
import httpx
import pytest
from kubernetes import client

def test_kubernetes_proxy(test_client, mock_settings):
    """Test the Kubernetes proxy endpoint"""
    # Ensure the mock_settings is being used in kubernetes_proxy function
    with patch("python.app.kubernetes_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings
        
        # Mock the httpx client
        with patch("httpx.AsyncClient") as mock_client:
            # Configure the mock client's response
            mock_response = MagicMock()
            mock_response.json.return_value = {"kind": "Pod", "items": []}
            
            # Configure the mock client's request method
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.request.return_value = mock_response
            mock_client.return_value = mock_client_instance
            
            # Create a proper async context manager mock for aiofiles.open
            async_mock = MagicMock()
            async_cm = MagicMock()
            async_cm.__aenter__.return_value.read.return_value = "test-token"
            async_mock.return_value = async_cm
            
            # Mock the token file reading using aiofiles with async context manager
            with patch("aiofiles.open", async_mock):
                # Test GET request to the proxy endpoint
                response = test_client.get("/kubernetes/pods")
                assert response.status_code == 200
                data = response.json()
                assert data["kind"] == "Pod"
                
                # Verify the request was made with the correct URL and headers
                call_kwargs = mock_client_instance.__aenter__.return_value.request.call_args[1]
                assert call_kwargs["url"] == f"{mock_settings.kubernetes_api_url}/api/v1/pods"
                assert "Authorization" in call_kwargs["headers"]
                assert call_kwargs["headers"]["Authorization"] == "Bearer test-token"

def test_kubernetes_proxy_failure(test_client):
    """Test the Kubernetes proxy endpoint when the API is unavailable"""
    # Mock httpx to raise an exception
    with patch("python.app.kubernetes_api.get_settings") as mock_get_settings:
        # Create a mock settings
        mock_settings = MagicMock()
        mock_settings.kubernetes_api_url = "https://test-kubernetes.local"
        mock_settings.verify_ssl = False
        mock_get_settings.return_value = mock_settings
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value.request.side_effect = httpx.HTTPError("Connection error")
            mock_client.return_value = mock_client_instance
            
            # Create a proper async context manager mock for aiofiles.open
            async_mock = MagicMock()
            async_cm = MagicMock()
            async_cm.__aenter__.return_value.read.return_value = "test-token"
            async_mock.return_value = async_cm
            
            # Mock the token file reading using aiofiles with async context manager
            with patch("aiofiles.open", async_mock):
                # Test request to the proxy endpoint
                response = test_client.get("/kubernetes/pods")
                assert response.status_code == 503
                assert "unavailable" in response.json()["detail"].lower()

def test_kubernetes_proxy_file_not_found():
    """Test the Kubernetes proxy when token file is not found."""
    from python.app.kubernetes_api import proxy as kubernetes_proxy
    import asyncio
    
    # Mock the request
    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/namespaces"
    
    # Mock get_settings to return a non-existent token path
    with patch('python.app.kubernetes_api.get_settings') as mock_settings:
        mock_config = MagicMock()
        mock_config.kubernetes_token_path = "/non/existent/path"
        mock_config.kubernetes_api_url = "https://kube.example.com"
        mock_settings.return_value = mock_config
        
        # Mock get_kubernetes_token to return None
        with patch('python.app.kubernetes_api.get_kubernetes_token') as mock_get_token:
            mock_get_token.return_value = None
            
            # Use asyncio.run to properly await the async function
            response = asyncio.run(kubernetes_proxy(mock_request))
            
            # Assert that we got an error response
            assert response.status_code == 500
            assert "Kubernetes authentication failed" in response.json()["detail"]

def test_kubernetes_proxy_permission_error():
    """Test the Kubernetes proxy when there's a permission error reading the token."""
    from python.app.kubernetes_api import proxy as kubernetes_proxy
    import asyncio
    
    # Mock the request
    mock_request = MagicMock()
    mock_request.url.path = "/api/v1/namespaces"
    
    # Mock get_settings to return a token path that will trigger a permission error
    with patch('python.app.kubernetes_api.get_settings') as mock_settings:
        mock_config = MagicMock()
        mock_config.kubernetes_token_path = "/etc/restricted/token"  # Path that would cause permission error
        mock_config.kubernetes_api_url = "https://kube.example.com"
        mock_settings.return_value = mock_config
        
        # Mock get_kubernetes_token to simulate a permission error
        with patch('python.app.kubernetes_api.get_kubernetes_token') as mock_get_token:
            mock_get_token.return_value = None  # Simulate token retrieval failure
            
            # Use asyncio.run to properly await the async function
            response = asyncio.run(kubernetes_proxy(mock_request))
            
            # Assert that we got an error response
            assert response.status_code == 500
            assert "Kubernetes authentication failed" in response.json()["detail"]

def test_kubernetes_proxy_post_request(test_client, mock_settings):
    """Test the Kubernetes proxy endpoint with POST request"""
    # Mock settings
    with patch("python.app.kubernetes_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings
        
        # Mock aiofiles.open
        async_mock = MagicMock()
        async_cm = MagicMock()
        async_cm.__aenter__.return_value.read.return_value = "test-token"
        async_mock.return_value = async_cm
        
        with patch("aiofiles.open", async_mock):
            # Mock httpx client
            with patch("httpx.AsyncClient") as mock_client:
                # Configure the mock client's response
                mock_response = MagicMock()
                mock_response.json.return_value = {"kind": "Pod", "metadata": {"name": "new-pod"}}
                
                # Configure the mock client instance
                mock_client_instance = MagicMock()
                mock_client_instance.__aenter__.return_value.request.return_value = mock_response
                mock_client.return_value = mock_client_instance
                
                # Test POST request to create a pod
                pod_data = {
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {"name": "new-pod"},
                    "spec": {"containers": [{"name": "nginx", "image": "nginx"}]}
                }
                
                response = test_client.post("/kubernetes/namespaces/default/pods", json=pod_data)
                
                # Verify response
                assert response.status_code == 200
                assert response.json()["kind"] == "Pod"
                
                # Verify request details
                call_kwargs = mock_client_instance.__aenter__.return_value.request.call_args[1]
                assert call_kwargs["method"] == "POST"
                assert call_kwargs["url"] == f"{mock_settings.kubernetes_api_url}/api/v1/namespaces/default/pods"
                assert call_kwargs["content"] is not None  # Body content should be present

def test_get_apps_v1_client():
    """Test the get_apps_v1_client function"""
    from python.app.kubernetes_api import get_apps_v1_client
    
    # Mock the Kubernetes client and configuration
    with patch("python.app.kubernetes_api.get_kubernetes_client") as mock_get_client, \
         patch("kubernetes.client.AppsV1Api") as mock_apps_api:
        
        # Configure mock AppsV1Api
        mock_apps_client = MagicMock()
        mock_apps_api.return_value = mock_apps_client
        
        # Call the function
        result = get_apps_v1_client()
        
        # Verify get_kubernetes_client was called to set up configuration
        mock_get_client.assert_called_once()
        
        # Verify AppsV1Api client was created and returned
        mock_apps_api.assert_called_once()
        assert result == mock_apps_client
