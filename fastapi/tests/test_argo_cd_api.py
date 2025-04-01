import pytest
from unittest.mock import patch, MagicMock
import httpx

def test_get_argo_cd_token_success(test_client, mock_settings):
    """Test successful Argo CD token retrieval"""
    with patch("httpx.AsyncClient") as mock_client:
        # Configure mock response for successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test-argo-cd-token"}
        
        # Configure mock client instance
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Import here to use the patched client
        from app.argo_cd_api import get_argo_cd_token
        import asyncio
        
        # Execute the function and verify the token
        token = asyncio.run(get_argo_cd_token())
        assert token == "test-argo-cd-token"
        
        # Verify the request was made with correct parameters
        mock_client_instance.__aenter__.return_value.post.assert_called_with(
            f"{mock_settings.argo_cd_url}/api/v1/session",
            json={"username": mock_settings.argo_cd_username, "password": mock_settings.argo_cd_password},
            timeout=10.0
        )

def test_get_argo_cd_token_failure(test_client, mock_settings):
    """Test Argo CD token retrieval when authentication fails"""
    with patch("httpx.AsyncClient") as mock_client:
        # Configure mock response for failed authentication
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        
        # Configure mock client instance
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.post.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Import here to use the patched client
        from app.argo_cd_api import get_argo_cd_token
        from fastapi import HTTPException
        import asyncio
        
        # Execute the function and verify it raises HTTPException
        with pytest.raises(HTTPException) as excinfo:
            asyncio.run(get_argo_cd_token())
        
        assert excinfo.value.status_code == 401
        assert "Authentication Failed" in excinfo.value.detail

def test_argo_cd_proxy(test_client, mock_argo_cd_token):
    """Test the Argo CD proxy endpoint"""
    # Mock the httpx client
    with patch("httpx.AsyncClient") as mock_client:
        # Configure mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"applications": []}
        
        # Configure mock client instance
        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__.return_value.request.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        # Test GET request to the proxy endpoint
        response = test_client.get("/argocd/applications")
        
        assert response.status_code == 200
        assert response.json() == {"applications": []}
        
        # Verify request was made with proper headers
        call_kwargs = mock_client_instance.__aenter__.return_value.request.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-argo-cd-token"
