import pytest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi import HTTPException

# Import the function to be tested at the module level
from app.argo_cd_api import get_argo_cd_token

@pytest.mark.asyncio
async def test_get_argo_cd_token_success(test_client, mock_settings):
    """Test successful Argo CD token retrieval"""
    # Configure the mock settings
    mock_settings.argo_cd_username = "m0ck!us3r"
    mock_settings.argo_cd_password = "M0ckPa%%w0rd"

    # Ensure the mock_settings is being used in get_argo_cd_token function
    with patch("app.argo_cd_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        # Create mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"token": "test-argo-cd-token"})

        # Create mock client instance returned by the context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        # Create mock context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_client_instance
        mock_cm.__aexit__.return_value = None

        # Patch AsyncClient where it's used in the argo_cd_api module
        with patch("app.argo_cd_api.httpx.AsyncClient") as MockAsyncClientClass:
            # Configure the instance returned by the async context manager
            MockAsyncClientClass.return_value.__aenter__.return_value = mock_client_instance
            MockAsyncClientClass.return_value.__aexit__.return_value = None

            # Execute the function and verify the token
            token = await get_argo_cd_token()
            assert token == "test-argo-cd-token"

            # Verify AsyncClient class was instantiated correctly
            MockAsyncClientClass.assert_called_once_with(verify=mock_settings.verify_ssl)

            # Verify the post method on the client instance was called
            mock_client_instance.post.assert_awaited_once_with(
                f"{mock_settings.argo_cd_url}/api/v1/session",
                json={
                    "username": mock_settings.argo_cd_username,
                    "password": mock_settings.argo_cd_password,
                },
                timeout=10.0,
            )


@pytest.mark.asyncio
async def test_get_argo_cd_token_failure(test_client, mock_settings):
    """Test Argo CD token retrieval when authentication fails"""
    # Configure the mock settings
    mock_settings.argo_cd_username = "m0ck!us3r"
    mock_settings.argo_cd_password = "M0ckPa%%w0rd"

    # Ensure the mock_settings is being used in get_argo_cd_token function
    with patch("app.argo_cd_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        # Create mock response
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"

        # Create mock client instance returned by the context manager
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        # Create mock context manager
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value = mock_client_instance
        mock_cm.__aexit__.return_value = None

        # Patch AsyncClient where it's used in the argo_cd_api module
        with patch("app.argo_cd_api.httpx.AsyncClient") as MockAsyncClientClass:
             # Configure the instance returned by the async context manager
            MockAsyncClientClass.return_value.__aenter__.return_value = mock_client_instance
            MockAsyncClientClass.return_value.__aexit__.return_value = None

            # Execute the function and verify it raises HTTPException
            with pytest.raises(HTTPException) as excinfo:
                await get_argo_cd_token()

            # Verify AsyncClient class was instantiated correctly
            MockAsyncClientClass.assert_called_once_with(verify=mock_settings.verify_ssl)

            # Verify the post method on the client instance was called
            mock_client_instance.post.assert_awaited_once()

            assert excinfo.value.status_code == 401
            assert "Authentication Failed" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_argo_cd_proxy(test_client, mock_settings):
    """Test the Argo CD proxy endpoint"""
    # Configure the mock settings
    mock_settings.argo_cd_username = "m0ck!us3r"
    mock_settings.argo_cd_password = "M0ckPa%%w0rd"

    # Ensure the mock_settings is being used
    with patch("app.argo_cd_api.get_settings") as mock_get_settings:
        mock_get_settings.return_value = mock_settings

        # Mock the get_argo_cd_token function
        with patch("app.argo_cd_api.get_argo_cd_auth_token") as mock_token:
            mock_token.return_value = "test-argo-cd-token"

            # Create mock response for the proxy request
            mock_proxy_response = AsyncMock()
            mock_proxy_response.json = AsyncMock(return_value={"applications": []})
            mock_proxy_response.status_code = 200

            # Create mock client for proxy
            mock_client = AsyncMock()
            mock_client.request = AsyncMock(return_value=mock_proxy_response)

            # Patch AsyncClient where it's used in the argo_cd_api module
            with patch("app.argo_cd_api.httpx.AsyncClient") as MockAsyncClientClass:
                # Configure the instance returned by the async context manager
                MockAsyncClientClass.return_value.__aenter__.return_value = mock_client
                MockAsyncClientClass.return_value.__aexit__.return_value = None

                # Test GET request to the proxy endpoint
                response = test_client.get("/argo/cd/applications")
                assert response.status_code == 200
                assert response.json() == {"applications": []}

                # Verify request was made with proper headers
                mock_client.request.assert_awaited_once()
