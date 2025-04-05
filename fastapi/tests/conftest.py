import pytest
import warnings
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI app instance

@pytest.fixture
def mock_settings():
    """Fixture to mock application settings"""
    with patch("app.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.kubernetes_api_url = "https://test-kubernetes.local"
        settings.kubernetes_token_path = "/tmp/test-kubernetes-token"
        settings.argo_cd_url = "https://test-argo-cd.local"
        settings.argo_cd_username = "m0cK!us3R"
        settings.argo_cd_password = "M0ckPa%%w0rd"
        settings.tvp_repo_url = "git@github.com:test/test-repo.git"
        settings.tvp_repo_path = "/tmp/test-repo"
        settings.tvp_branch = "main"
        settings.environment = "test"
        settings.verify_ssl = False
        mock_get_settings.return_value = settings
        yield settings # Yield the settings object

@pytest.fixture
def mock_kubernetes_client():
    """Fixture to mock Kubernetes client where it's used in main.py"""
    with patch("app.main.get_kubernetes_client") as mock_client: # Target app.main
        kubernetes_client = MagicMock()
        # Ensure list_namespace doesn't raise an exception for healthy check
        kubernetes_client.list_namespace.return_value = MagicMock()
        mock_client.return_value = kubernetes_client
        yield kubernetes_client

@pytest.fixture
def mock_argo_cd_token():
    """Fixture to mock Argo CD authentication token where it's used in main.py"""
    with patch("app.main.get_argo_cd_token") as mock_token: # Target app.main
        # Make this an async mock to work with the async function
        from unittest.mock import AsyncMock
        # Ensure it doesn't raise an exception for healthy check
        mock_token.return_value = "test-argo-cd-token" # Use return_value for async mock
        yield mock_token

@pytest.fixture
def mock_git_commands():
    """Fixture to mock Git subprocess commands"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run

@pytest.fixture
def mock_yaml_operations():
    """Fixture to mock YAML operations"""
    with patch("yaml.safe_load") as mock_yaml_load:
        mock_yaml_load.return_value = {
            "image": "test-image",
            "tag": "latest",
        }
        yield mock_yaml_load

# Define a single, simple test_client fixture
@pytest.fixture
def test_client(mock_settings): # Only depend on settings if needed globally
    """Fixture to create a FastAPI TestClient"""
    from app.main import app
    client = TestClient(app)
    yield client
# Remove the duplicate/complex test_client fixture below

@pytest.fixture
def test_health_check_kubernetes_unhealthy():
    """Special fixture to mock Kubernetes client for health check tests"""
    with patch("app.main.get_kubernetes_client") as mock_client:
        kubernetes_client = MagicMock()
        kubernetes_client.list_namespace.side_effect = Exception("Connection refused")
        mock_client.return_value = kubernetes_client
        yield mock_client

@pytest.fixture
def test_health_check_argo_cd_unhealthy():
    """Special fixture to mock Argo CD token for health check tests"""
    with patch("app.main.get_argo_cd_token") as mock_token:
        mock_token.side_effect = Exception("Argo CD unavailable")
        yield mock_token
