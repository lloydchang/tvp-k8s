"""Test module for argo_cd_api.py with 100% coverage"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from ..app.argo_cd_api import get_argo_cd_token, get_argo_cd_auth_token, argo_cd_proxy

@pytest.mark.asyncio
async def test_get_argo_cd_token_development_mode():
    """Test get_argo_cd_token in development mode."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock for development mode
        mock_settings.return_value.environment = "development"
        mock_settings.return_value.argo_cd_username = "admin"
        mock_settings.return_value.argo_cd_password = "password"
        mock_settings.return_value.verify_ssl = False
            
        # Test with successful client
        token = await get_argo_cd_token()
        assert token == "mock-dev-token-for-argocd"

@pytest.mark.asyncio
async def test_get_argo_cd_token_development_mode_no_password():
    """Test get_argo_cd_token in development mode with no password."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock for development mode without password
        mock_settings.return_value.environment = "development"
        mock_settings.return_value.argo_cd_username = "admin"
        mock_settings.return_value.argo_cd_password = None
        mock_settings.return_value.verify_ssl = False
            
        # Test with no password
        token = await get_argo_cd_token()
        assert token == "mock-dev-token-for-argocd"

@pytest.mark.asyncio
async def test_get_argo_cd_token_development_mode_exception():
    """Test get_argo_cd_token in development mode with exception."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock for development mode
        mock_settings.return_value.environment = "development"
        mock_settings.return_value.argo_cd_username = "admin"
        mock_settings.return_value.argo_cd_password = "password"
        mock_settings.return_value.verify_ssl = False
        
        # Force an exception during client initialization
        mock_client.side_effect = Exception("Test error")
            
        # Should fall back to mock token in dev mode
        token = await get_argo_cd_token()
        assert token == "mock-dev-token-for-argocd"

@pytest.mark.asyncio
async def test_get_argo_cd_token_production_mode():
    """Test get_argo_cd_token in production mode."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock for production mode
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_username = "admin"
        mock_settings.return_value.argo_cd_password = "password"
        mock_settings.return_value.verify_ssl = True
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
        
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"token": "production-token"})
        mock_client_instance.post.return_value = mock_response
        
        # Call the function
        token = await get_argo_cd_token()
        
        # Verify token and request
        assert token == "production-token"
        mock_client_instance.post.assert_called_once_with(
            f"{mock_settings.return_value.argo_cd_url}/api/v1/session",
            json={
                "username": mock_settings.return_value.argo_cd_username,
                "password": mock_settings.return_value.argo_cd_password
            },
            timeout=10.0
        )

@pytest.mark.asyncio
async def test_get_argo_cd_token_production_mode_no_password():
    """Test get_argo_cd_token in production mode with no password."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings:
        # Configure settings mock for production mode without password
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_password = None
                
        # Should raise an exception
        with pytest.raises(HTTPException) as exc_info:
            await get_argo_cd_token()
                
        assert exc_info.value.status_code == 500
        assert "Argo CD password not configured" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_argo_cd_token_production_mode_auth_failure():
    """Test get_argo_cd_token in production mode with authentication failure."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
                
        # Configure settings mock for production mode
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_username = "admin"
        mock_settings.return_value.argo_cd_password = "password"
        mock_settings.return_value.verify_ssl = True
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
                
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
                
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_client_instance.post.return_value = mock_response
                
        # Should raise an exception
        with pytest.raises(HTTPException) as exc_info:
            await get_argo_cd_token()
                
        assert exc_info.value.status_code == 401
        assert "Argo CD Authentication Failed" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_argo_cd_token_production_mode_network_error():
    """Test get_argo_cd_token in production mode with network error."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
                
        # Configure settings mock for production mode
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_username = "admin"
        mock_settings.return_value.argo_cd_password = "password"
        mock_settings.return_value.verify_ssl = True
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
                
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
                
        # Mock network error
        mock_client_instance.post.side_effect = httpx.RequestError("Connection error")
                
        # Should raise an exception
        with pytest.raises(HTTPException) as exc_info:
            await get_argo_cd_token()
                
        assert exc_info.value.status_code == 503
        assert "Argo CD service unavailable" in exc_info.value.detail

@pytest.mark.asyncio
async def test_get_argo_cd_auth_token_alias():
    """Test that get_argo_cd_auth_token is an alias to get_argo_cd_token."""
    with patch('python.app.argo_cd_api.get_argo_cd_token') as mock_token:
        mock_token.return_value = "test-token"
        token = await get_argo_cd_auth_token()
        assert token == "test-token"
        mock_token.assert_called_once()

@pytest.mark.asyncio
async def test_argo_cd_proxy_development_mock():
    """Test argo_cd_proxy with development mode and mock data."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.get_argo_cd_auth_token') as mock_token:
        
        # Configure settings mock for development mode
        mock_settings.return_value.environment = "development"
        
        # Configure mock request
        mock_request = MagicMock()
        mock_request.method = "GET"
        
        # Call with applications path
        result = await argo_cd_proxy("applications", mock_request)
        
        # Should return mock data
        assert "items" in result
        assert result["items"][0]["metadata"]["name"] == "example-app"
        assert not mock_token.called

@pytest.mark.asyncio
async def test_argo_cd_proxy_development_other_path():
    """Test argo_cd_proxy with development mode and a non-mocked path."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.get_argo_cd_auth_token') as mock_token, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock for development mode
        mock_settings.return_value.environment = "development"
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
        mock_settings.return_value.verify_ssl = False
        
        # Configure auth token mock
        mock_token.return_value = "mock-token"
        
        # Configure mock request
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers = {"Content-Type": "application/json", "Host": "localhost"}
        
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"result": "success"})
        mock_client_instance.request.return_value = mock_response
        
        # Call with a different path
        result = await argo_cd_proxy("clusters", mock_request)
        
        # Verify result and request
        assert result == {"result": "success"}
        mock_token.assert_called_once()
        mock_client_instance.request.assert_called_once_with(
            method="GET",
            url=f"{mock_settings.return_value.argo_cd_url}/api/v1/clusters",
            headers={"Authorization": f"Bearer {mock_token.return_value}", "Content-Type": "application/json"},
            content=None,
            follow_redirects=True
        )

@pytest.mark.asyncio
async def test_argo_cd_proxy_production_mode():
    """Test argo_cd_proxy in production mode."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.get_argo_cd_auth_token') as mock_token, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock for production mode
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
        mock_settings.return_value.verify_ssl = True
        
        # Configure auth token mock
        mock_token.return_value = "production-token"
        
        # Configure mock request
        mock_request = MagicMock()
        mock_request.method = "POST"
        mock_request.headers = {"Content-Type": "application/json", "Host": "example.com"}
        mock_request.body = AsyncMock(return_value=b'{"key": "value"}')
        
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"result": "created"})
        mock_client_instance.request.return_value = mock_response
        
        # Call with POST request
        result = await argo_cd_proxy("applications", mock_request)
        
        # Verify result and request
        assert result == {"result": "created"}
        mock_token.assert_called_once()
        mock_client_instance.request.assert_called_once_with(
            method="POST",
            url=f"{mock_settings.return_value.argo_cd_url}/api/v1/applications",
            headers={"Authorization": f"Bearer {mock_token.return_value}", "Content-Type": "application/json"},
            content=b'{"key": "value"}',
            follow_redirects=True
        )

@pytest.mark.asyncio
async def test_argo_cd_proxy_json_error():
    """Test argo_cd_proxy with non-JSON response."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.get_argo_cd_auth_token') as mock_token, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
        mock_settings.return_value.verify_ssl = True
        
        # Configure auth token mock
        mock_token.return_value = "test-token"
        
        # Configure mock request
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers = {}
        
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock response with non-JSON content
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = "Not JSON content"
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client_instance.request.return_value = mock_response
        
        # Call the function
        result = await argo_cd_proxy("settings", mock_request)
        
        # Verify result fallback to text
        assert result["status_code"] == 200
        assert result["content"] == "Not JSON content"

@pytest.mark.asyncio
async def test_argo_cd_proxy_http_error():
    """Test argo_cd_proxy with HTTP error."""
    with patch('python.app.argo_cd_api.get_settings') as mock_settings, \
         patch('python.app.argo_cd_api.get_argo_cd_auth_token') as mock_token, \
         patch('python.app.argo_cd_api.httpx.AsyncClient') as mock_client:
        
        # Configure settings mock
        mock_settings.return_value.environment = "production"
        mock_settings.return_value.argo_cd_url = "https://argocd.example.com"
        mock_settings.return_value.verify_ssl = True
        
        # Configure auth token mock
        mock_token.return_value = "test-token"
        
        # Configure mock request
        mock_request = MagicMock()
        mock_request.method = "GET"
        mock_request.headers = {}
        
        # Mock the AsyncClient context
        mock_client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # Mock HTTP error
        mock_client_instance.request.side_effect = httpx.HTTPError("Connection error")
        
        # Should raise an exception
        with pytest.raises(HTTPException) as exc_info:
            await argo_cd_proxy("applications", mock_request)
        
        assert exc_info.value.status_code == 503
        assert "Argo CD API unavailable" in exc_info.value.detail
