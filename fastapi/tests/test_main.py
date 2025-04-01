import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_root_endpoint(test_client):
    """Test the root endpoint returns correct information"""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Kubernetes Platform API"
    assert "version" in data
    assert "endpoints" in data
    assert len(data["endpoints"]) == 3

def test_health_check_all_healthy(test_client):
    """Test the health check endpoint when all services are healthy"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["kubernetes"]["status"] == "healthy"
    assert data["services"]["argocd"]["status"] == "healthy"

def test_health_check_kubernetes_unhealthy(test_client, mock_kubernetes_client):
    """Test health check when Kubernetes is not available"""
    mock_kubernetes_client.list_namespace.side_effect = Exception("Connection refused")
    
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["kubernetes"]["status"] == "unhealthy"
    assert "error" in data["services"]["kubernetes"]

def test_health_check_argocd_unhealthy(test_client, mock_argocd_token):
    """Test health check when ArgoCD is not available"""
    mock_argocd_token.side_effect = Exception("ArgoCD unavailable")
    
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["argocd"]["status"] == "unhealthy"
    assert "error" in data["services"]["argocd"]
