import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_root_endpoint(test_client):
    """Test the root endpoint returns correct information"""
    response = test_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TVP API"
    assert "version" in data
    assert "endpoints" in data
    
    # Check the new endpoints structure
    assert len(data["endpoints"]) == 4
    
    # Get all endpoint prefixes for easier assertion
    endpoint_prefixes = [ep["prefix"] for ep in data["endpoints"]]
    
    # Check that the current paths are present
    assert "/deploy" in endpoint_prefixes
    assert "/reconcile" in endpoint_prefixes
    assert "/argo/cd" in endpoint_prefixes
    assert "/kubernetes" in endpoint_prefixes
    
    # Old paths should not be present
    assert "/gitops/deployments" not in endpoint_prefixes
    assert "/gitops" not in endpoint_prefixes

def test_health_check_all_healthy(test_client, mock_kubernetes_client, mock_argo_cd_token):
    """Test the health check endpoint when all services are healthy"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["kubernetes"]["status"] == "healthy"
    assert data["services"]["argo_cd"]["status"] == "healthy"

def test_health_check_kubernetes_unhealthy(test_client, test_health_check_kubernetes_unhealthy):
    """Test health check when Kubernetes is not available"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["kubernetes"]["status"] == "unhealthy"
    assert "error" in data["services"]["kubernetes"]

def test_health_check_argo_cd_unhealthy(test_client, test_health_check_argo_cd_unhealthy):
    """Test health check when Argo CD is not available"""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["argo_cd"]["status"] == "unhealthy"
    assert "error" in data["services"]["argo_cd"]