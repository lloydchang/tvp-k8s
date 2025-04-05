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
api_dir = str(Path(__file__).parent.parent)
sys.path.insert(0, api_dir)

# Patch GitOps reconciliation thread to avoid actual thread creation in tests
with patch('python.app.gitops.start_reconciliation_thread') as mock_start_thread:
    mock_start_thread.return_value = None
    
    # Import the app after path modifications
    from api.index import app

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as client:
        yield client

# Mock the settings to avoid reading actual configuration files
@pytest.fixture
def mock_settings():
    """Mock Settings to use test values."""
    with patch('python.app.config.get_settings') as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.kubernetes_api_url = "https://kubernetes.example.com"
        mock_settings.argo_cd_api_url = "https://argocd.example.com"
        mock_settings.argo_cd_username = "test-user"
        mock_settings.argo_cd_password = "test-password"
        mock_settings.verify_ssl = False
        mock_settings.gitops_repo_url = "https://github.com/example/repo.git"
        mock_settings.gitops_repo_path = "/tmp/test-gitops-repo"
        mock_settings.gitops_repo_branch = "main"
        
        mock_get_settings.return_value = mock_settings
        yield mock_settings

# Additional mock for Git commands
@pytest.fixture
def mock_git_commands():
    """Mock Git commands to avoid actual Git operations."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock_run

@pytest.fixture
def mock_kubernetes_client():
    """Fixture to mock Kubernetes client where it's used in index.py"""
    with patch("python.app.config.get_kubernetes_client") as mock_get_client_function:
        # First, patch the function that gets the client
        kubernetes_client = MagicMock()
        # Create a specific mock for list_namespace that won't make actual API calls
        namespace_list = MagicMock()
        namespace_list.items = [MagicMock()]  # Add at least one namespace to indicate it's healthy
        kubernetes_client.list_namespace = MagicMock(return_value=namespace_list)
        mock_get_client_function.return_value = kubernetes_client
        
        # Now, also patch the direct import in index.py
        with patch("api.index.get_kubernetes_client") as mock_index_client:
            mock_index_client.return_value = kubernetes_client
            yield kubernetes_client

@pytest.fixture
def mock_argo_cd_token():
    """Fixture to mock Argo CD authentication token where it's used in index.py"""
    with patch("api.index.get_argo_cd_token") as mock_token:
        # Make this an async mock to work with the async function
        from unittest.mock import AsyncMock
        mock_async = AsyncMock()
        mock_async.return_value = "test-argo-cd-token"
        mock_token.side_effect = mock_async
        yield mock_token

@pytest.fixture
def mock_yaml_operations():
    """Fixture to mock YAML operations"""
    with patch("yaml.safe_load") as mock_yaml_load:
        mock_yaml_load.return_value = {
            "image": "test-image",
            "tag": "latest",
        }
        yield mock_yaml_load

@pytest.fixture
def test_health_check_kubernetes_unhealthy(test_client):
    """Special fixture to mock Kubernetes client for health check tests where it's unhealthy"""
    with patch("api.index.get_kubernetes_client") as mock_client:
        k8s_client = MagicMock()
        k8s_client.list_namespace = MagicMock(side_effect=Exception("Connection refused"))
        mock_client.return_value = k8s_client
        yield test_client

@pytest.fixture
def test_health_check_argo_cd_unhealthy(test_client):
    """Special fixture to mock Argo CD token for health check tests where it's unhealthy"""
    with patch("api.index.get_argo_cd_token") as mock_token:
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
