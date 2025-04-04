import pytest
from unittest.mock import patch, MagicMock

def test_get_argo_cd_token_success(test_client, mock_settings):
    """Test successful Argo CD token retrieval"""
    # Configure the argo_cd_identity property on the mock
    mock_settings.argo_cd_identity = mock_settings.argo_cd_username
    
    # Ensure the mock_settings is being used in get_argo_cd_token function
    with patch("app.argo_cd_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings
        
        # Use AsyncMock for proper async behavior
        from unittest.mock import AsyncMock
        
        # Mock the client as an async context manager
        mock_client = AsyncMock()
        
        # Configure mock response for successful authentication
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test-argo-cd-token"}
        
        # Configure post method to return the mock response
        mock_client.post = AsyncMock(return_value=mock_response)
        
        # Patch AsyncClient with our async mock
        with patch("httpx.AsyncClient", return_value=mock_client):
            # Import here to use the patched client
            from app.argo_cd_api import get_argo_cd_token
            import asyncio
            
            # Execute the function and verify the token
            token = asyncio.run(get_argo_cd_token())
            assert token == "test-argo-cd-token"
            
            # Verify the request was made with correct parameters
            mock_client.post.assert_called_with(
                f"{mock_settings.argo_cd_url}/api/v1/session",
                json={"identity": mock_settings.argo_cd_identity},
                timeout=10.0
            )

def test_get_argo_cd_token_failure(test_client, mock_settings):
    """Test Argo CD token retrieval when authentication fails"""
    # Configure the argo_cd_identity property on the mock
    mock_settings.argo_cd_identity = mock_settings.argo_cd_username
    
    # Ensure the mock_settings is being used in get_argo_cd_token function
    with patch("app.argo_cd_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings
        
        with patch("httpx.AsyncClient.__aenter__") as mock_client:
            # Configure mock response for failed authentication
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Invalid credentials"
            
            # Configure mock client's post method
            mock_client.return_value.post = MagicMock()
            mock_client.return_value.post.return_value = mock_response
            
            # Import here to use the patched client
            from app.argo_cd_api import get_argo_cd_token
            from fastapi import HTTPException
            import asyncio
            
            # Execute the function and verify it raises HTTPException
            with pytest.raises(HTTPException) as excinfo:
                asyncio.run(get_argo_cd_token())
            
            assert excinfo.value.status_code == 401
            assert "Authentication Failed" in excinfo.value.detail

def test_argo_cd_proxy(test_client, mock_settings):
    """Test the Argo CD proxy endpoint"""
    # Ensure the mock_settings is being used
    with patch("app.argo_cd_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings
        
        # Mock the get_argo_cd_token function directly
        with patch("app.argo_cd_api.get_argo_cd_auth_token") as mock_token:
            # Configure the token function to return a test token
            mock_token.return_value = "test-argo-cd-token"
            
            # Mock the httpx client
            with patch("httpx.AsyncClient.__aenter__") as mock_client:
                # Configure mock response
                mock_response = MagicMock()
                mock_response.json.return_value = {"applications": []}
                
                # Configure mock client's request method
                mock_client.return_value.request = MagicMock()
                mock_client.return_value.request.return_value = mock_response
                
                # Test GET request to the proxy endpoint
                response = test_client.get("/argo/cd/applications")
                
                assert response.status_code == 200
                assert response.json() == {"applications": []}
                
                # Verify request was made with proper headers
                call_kwargs = mock_client.return_value.request.call_args[1]
                assert "Authorization" in call_kwargs["headers"]
                assert call_kwargs["headers"]["Authorization"] == "Bearer test-argo-cd-token"
