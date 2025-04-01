from unittest.mock import patch, MagicMock, mock_open
import httpx

def test_kubernetes_proxy(test_client, mock_settings):
    """Test the Kubernetes proxy endpoint"""
    # Mock the httpx client
    with patch("httpx.AsyncClient") as mock_client:
        # Configure the mock client's response
        mock_response = MagicMock()
        mock_response.json.return_value = {"kind": "Pod", "items": []}
        
        # Configure the mock client's request method
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.request.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Use mock_open to mock file reading operations
        token_content = "test-token"
        with patch("builtins.open", mock_open(read_data=token_content)):
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
    with patch("httpx.AsyncClient") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.request.side_effect = httpx.HTTPError("Connection error")
        mock_client.return_value = mock_client_instance
        
        # Mock the token file
        with patch("builtins.open", MagicMock()):
            with patch("fastapi.kubernetes_api.open", MagicMock()):
                # Test request to the proxy endpoint
                response = test_client.get("/kubernetes/pods")
                assert response.status_code == 503
                assert "unavailable" in response.json()["detail"].lower()
