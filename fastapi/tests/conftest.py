import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

@pytest.fixture
def mock_settings():
    """Fixture to mock application settings"""
    with patch("app.config.get_settings") as mock_get_settings:
        settings = MagicMock()
        settings.kubernetes_api_url = "https://test-kubernetes.local"
        settings.kubernetes_token_path = "/tmp/test-k8s-token"
        settings.argocd_url = "https://test-argocd.local"
        settings.argocd_username = "test-user"
        settings.argocd_password = "test-password"
        settings.tvp_repo_url = "git@github.com:test/test-repo.git"
        settings.tvp_repo_path = "/tmp/test-repo"
        settings.tvp_branch = "main"
        settings.environment = "test"
        settings.verify_ssl = False
        mock_get_settings.return_value = settings
        yield settings

@pytest.fixture
def mock_kubernetes_client():
    """Fixture to mock Kubernetes client"""
    with patch("app.config.get_kubernetes_client") as mock_client:
        k8s_client = MagicMock()
        k8s_client.list_namespace.return_value = MagicMock()
        mock_client.return_value = k8s_client
        yield k8s_client

@pytest.fixture
def mock_argocd_token():
    """Fixture to mock ArgoCD authentication token"""
    with patch("app.argocd_api.get_argocd_token") as mock_token:
        mock_token.return_value = "test-argocd-token"
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
            "tag": "latest"
        }
        yield mock_yaml_load

@pytest.fixture
def test_client(mock_settings, mock_kubernetes_client, mock_argocd_token):
    """Fixture to create a FastAPI TestClient"""
    from fastapi.main import app
    with TestClient(app) as client:
        yield client
