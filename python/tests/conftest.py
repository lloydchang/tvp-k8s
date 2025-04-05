import pytest
import warnings
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

# Make sure system packages are prioritized over local directories
# by temporarily removing the current directory from sys.path
cwd = ""
if "" in sys.path:
    cwd = sys.path.pop(sys.path.index(""))
    
# Also remove the current directory if it's in the path
current_dir = str(Path(__file__).parent.parent)
if (current_dir in sys.path):
    sys.path.remove(current_dir)

# Add the API directory to the Python path so we can import index.py
api_path = Path(__file__).parent.parent.parent / 'api'
sys.path.append(str(api_path))

# Now we can import from the api directory
try:
    import index
finally:
    # Restore the original path if we removed it
    if cwd:
        sys.path.insert(0, cwd)

@pytest.fixture
def mock_settings():
    """Fixture to mock application settings"""
    # Fix: Change from "api.config.get_settings" to "app.config.get_settings"
    with patch("app.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.kubernetes_api_url = "https://test-kubernetes.local"
        settings.kubernetes_token_path = "/tmp/test-kubernetes-token"
        settings.argo_cd_url = "https://test-argo-cd.local"
        settings.argo_cd_username = "m0cK!us3R"
        settings.argo_cd_password = "M0ckPa%%w0rd"
        settings.gitops_repo_url = "git@github.com:test/test-repo.git"
        settings.gitops_repo_path = "/tmp/test-repo"
        settings.gitops_repo_branch = "main"
        settings.environment = "test"
        settings.verify_ssl = False
        mock_get_settings.return_value = settings
        yield settings # Yield the settings object

@pytest.fixture
def mock_kubernetes_client():
    """Fixture to mock Kubernetes client where it's used in index.py"""
    with patch("app.config.get_kubernetes_client") as mock_get_client_function:
        # First, patch the function that gets the client
        kubernetes_client = MagicMock()
        # Create a specific mock for list_namespace that won't make actual API calls
        namespace_list = MagicMock()
        namespace_list.items = [MagicMock()]  # Add at least one namespace to indicate it's healthy
        kubernetes_client.list_namespace = MagicMock(return_value=namespace_list)
        mock_get_client_function.return_value = kubernetes_client
        
        # Now, also patch the direct import in index.py
        with patch("index.get_kubernetes_client") as mock_index_client:
            mock_index_client.return_value = kubernetes_client
            yield kubernetes_client

@pytest.fixture
def mock_argo_cd_token():
    """Fixture to mock Argo CD authentication token where it's used in index.py"""
    # Fix: Change from "api.index.get_argo_cd_token" to "index.get_argo_cd_token"
    with patch("index.get_argo_cd_token") as mock_token:
        # Make this an async mock to work with the async function
        from unittest.mock import AsyncMock
        mock_async = AsyncMock()
        mock_async.return_value = "test-argo-cd-token"
        mock_token.side_effect = mock_async
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
def test_client(mock_settings, mock_kubernetes_client, mock_argo_cd_token):
    """Fixture to create a FastAPI TestClient with all dependencies properly mocked"""
    with patch("index.get_kubernetes_client") as mock_get_k8s:
        # Set up a mock that returns a client that won't raise exceptions
        k8s_client = MagicMock()
        namespace_list = MagicMock()
        namespace_list.items = [MagicMock()]
        k8s_client.list_namespace = MagicMock(return_value=namespace_list)
        mock_get_k8s.return_value = k8s_client
        
        # Also patch the Argo CD token function in the main app
        with patch("index.get_argo_cd_token") as mock_get_token:
            from unittest.mock import AsyncMock
            mock_async = AsyncMock()
            mock_async.return_value = "test-argo-cd-token"
            mock_get_token.side_effect = mock_async
            
            from index import app
            client = TestClient(app)
            yield client

@pytest.fixture
def test_health_check_kubernetes_unhealthy(test_client):
    """Special fixture to mock Kubernetes client for health check tests where it's unhealthy"""
    with patch("index.get_kubernetes_client") as mock_client:
        k8s_client = MagicMock()
        k8s_client.list_namespace = MagicMock(side_effect=Exception("Connection refused"))
        mock_client.return_value = k8s_client
        yield test_client

@pytest.fixture
def test_health_check_argo_cd_unhealthy(test_client):
    """Special fixture to mock Argo CD token for health check tests where it's unhealthy"""
    with patch("index.get_argo_cd_token") as mock_token:
        mock_token.side_effect = Exception("Argo CD unavailable")
        yield test_client

@pytest.fixture(autouse=True)
def suppress_connection_warnings():
    """Fixture to suppress connection warnings from urllib3 during tests"""
    # Filter out specific connection warnings that are expected during tests
    warnings.filterwarnings("ignore", 
                           category=Warning,
                           message=".*Connection.*",
                           module="urllib3.connectionpool")
    yield
