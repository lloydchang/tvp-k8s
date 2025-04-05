from unittest.mock import patch, MagicMock, mock_open
import httpx

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
