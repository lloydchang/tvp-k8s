import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import os
import threading

def test_tvp_status_endpoint(test_client, mock_settings):
    """Test the TVP status endpoint"""
    # Mock Path.exists and Path.iterdir
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.iterdir") as mock_iterdir, \
         patch("pathlib.Path.is_dir") as mock_is_dir, \
         patch("builtins.open", MagicMock()), \
         patch("yaml.safe_load") as mock_yaml_load:
        
        # Setup mocks
        mock_exists.return_value = True
        
        # Mock directory structure
        namespace_dir = MagicMock()
        namespace_dir.name = "test-namespace"
        namespace_dir.is_dir.return_value = True
        
        app_dir = MagicMock()
        app_dir.name = "test-app"
        app_dir.is_dir.return_value = True
        
        values_file = MagicMock()
        values_file.exists.return_value = True
        
        # Setup directory structure for iterdir calls
        namespace_dir.iterdir.return_value = [app_dir]
        mock_iterdir.return_value = [namespace_dir]
        
        # Setup Path/file for values.yaml using a custom __truediv__ implementation
        def mock_truediv(self, other):
            if other == "values.yaml":
                return values_file
            elif other == "test-namespace":
                return namespace_dir
            return MagicMock()
        
        MagicMock.__truediv__ = mock_truediv
        
        # Configure YAML load mock
        mock_yaml_load.return_value = {
            "image": "test-image",
            "tag": "v1.0.0"
        }
        
        # Test the TVP status endpoint
        response = test_client.get("/tvp/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "is_reconciling" in data
        assert "applications" in data
        assert len(data["applications"]) == 1
        assert data["applications"][0]["app_name"] == "test-app"
        assert data["applications"][0]["namespace"] == "test-namespace"
        assert data["applications"][0]["image"] == "test-image"
        assert data["applications"][0]["tag"] == "v1.0.0"

def test_trigger_reconciliation(test_client):
    """Test the reconciliation trigger endpoint"""
    # Mock the reconciliation function to avoid actual execution
    with patch("app.tvp.reconcile_from_git") as mock_reconcile:
        # Set global flag to simulate not already reconciling
        import app.tvp as tvp
        tvp.is_reconciling = False
        
        # Test the reconciliation endpoint
        response = test_client.post("/tvp/reconcile")
        
        assert response.status_code == 200
        assert response.json()["status"] == "started"
        
        # Test that background task was added (can't directly verify)
        # but we can check that reconcile_from_git was imported

def test_trigger_reconciliation_already_running(test_client):
    """Test the reconciliation trigger when already in progress"""
    # Set global flag to simulate already reconciling
    import app.tvp as tvp
    tvp.is_reconciling = True
    
    # Test the reconciliation endpoint
    response = test_client.post("/tvp/reconcile")
    
    assert response.status_code == 200
    assert response.json()["status"] == "already_running"
    
    # Reset the flag for other tests
    tvp.is_reconciling = False

def test_trigger_reconciliation_background_task(test_client):
    """Test that the reconciliation task is properly added to background tasks"""
    import app.tvp as tvp
    tvp.is_reconciling = False
    
    # Create a mock for background_tasks
    mock_tasks = MagicMock()
    
    # Test with our mocked background tasks
    with patch("fastapi.BackgroundTasks", return_value=mock_tasks):
        response = test_client.post("/tvp/reconcile")
        
        # Verify that add_task was called with reconcile_from_git
        mock_tasks.add_task.assert_called_once_with(tvp.reconcile_from_git)
        
        # Check the response
        assert response.status_code == 200
        assert response.json()["status"] == "started"

def test_get_deployment_status(test_client, mock_settings):
    """Test getting deployment status for a specific app"""
    # Mock Path operations
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("builtins.open", MagicMock()), \
         patch("yaml.safe_load") as mock_yaml_load, \
         patch("app.tvp.get_last_reconciliation_time") as mock_get_time:
        
        # Setup mocks
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            "image": "test-image",
            "tag": "v1.0.0"
        }
        mock_get_time.return_value = "2023-07-01T12:00:00"
        
        # Test the deployment status endpoint
        response = test_client.get("/tvp/status/test-namespace/test-app")
        
        assert response.status_code == 200
        data = response.json()
        assert data["application"] == "test-app"
        assert data["namespace"] == "test-namespace"
        assert data["image"] == "test-image"
        assert data["tag"] == "v1.0.0"
        assert data["status"] == "deployed"
        assert data["last_reconciliation"] == "2023-07-01T12:00:00"
