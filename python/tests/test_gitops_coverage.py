"""
Test file for specific coverage paths in the GitOps module.
These tests are designed to hit specific lines and branches 
that are difficult to reach through normal testing.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import yaml
from subprocess import CalledProcessError
import asyncio

def test_reconcile_lock_acquisition_failure():
    """Test reconciliation lock acquisition failure"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Set up a mock lock that raises a RuntimeError when entering context
    mock_lock = MagicMock()
    mock_lock.__enter__.side_effect = RuntimeError("Lock acquisition failed")
    
    # Store original lock to restore after test
    original_lock = gitops.reconciliation_lock
    
    try:
        # Replace with our mocked lock
        gitops.reconciliation_lock = mock_lock
        
        # Call the function which should handle the lock failure gracefully
        reconcile_from_git()
        
        # Verify the lock was attempted
        mock_lock.__enter__.assert_called_once()
    finally:
        # Restore original lock
        gitops.reconciliation_lock = original_lock

def test_reconcile_lock_reset_failure():
    """Test reconciliation lock reset failure when setting is_reconciling back to False"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Set up mocks for repository existence/updates
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("python.app.gitops._update_repository"), \
         patch("python.app.gitops._apply_configurations_from_git"), \
         patch("python.app.gitops.set_last_reconciliation_time"):
        
        mock_exists.return_value = True
        
        # Set up a lock that succeeds on first enter but fails on second enter
        mock_lock = MagicMock()
        call_count = 0
        
        def side_effect_enter(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Second lock acquisition failed")
            return mock_lock
        
        mock_lock.__enter__ = MagicMock(side_effect=side_effect_enter)
        
        # Store original lock to restore after test
        original_lock = gitops.reconciliation_lock
        original_is_reconciling = gitops.is_reconciling
        
        try:
            # Replace with our mocked lock and set flag
            gitops.reconciliation_lock = mock_lock
            gitops.is_reconciling = False
            
            # Call the function - should still reset is_reconciling despite lock failure
            reconcile_from_git()
            
            # Verify lock was attempted twice
            assert mock_lock.__enter__.call_count == 2
            
            # Verify is_reconciling was reset to False even without the lock
            assert gitops.is_reconciling is False
        finally:
            # Restore original state
            gitops.reconciliation_lock = original_lock
            gitops.is_reconciling = original_is_reconciling

def test_start_thread_runtime_error():
    """Test error handling when thread.start() raises RuntimeError"""
    from python.app.gitops import start_reconciliation_thread
    
    # Mock the Thread class
    with patch("threading.Thread") as mock_thread_class:
        # Create a mock thread instance
        mock_thread = MagicMock()
        
        # Configure the mock to raise RuntimeError when start() is called
        mock_thread.start.side_effect = RuntimeError("Cannot start thread")
        mock_thread_class.return_value = mock_thread
        
        # Call the function and expect it to raise an Exception
        with pytest.raises(Exception) as excinfo:
            start_reconciliation_thread()
        
        # Verify error message
        assert "Failed to start reconciliation thread" in str(excinfo.value)
        
        # Verify thread was created but not stored in global var since start failed
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()

def test_start_thread_other_exception():
    """Test error handling when thread creation raises an unexpected exception"""
    from python.app.gitops import start_reconciliation_thread
    
    # Mock the Thread class to raise a generic Exception
    with patch("threading.Thread") as mock_thread_class:
        # Configure the mock to raise Exception when called
        mock_thread_class.side_effect = Exception("Thread creation failed")
        
        # Call the function and expect it to raise an Exception
        with pytest.raises(Exception) as excinfo:
            start_reconciliation_thread()
        
        # Verify error message
        assert "Failed to create reconciliation thread" in str(excinfo.value)
        
        # Verify thread creation was attempted
        mock_thread_class.assert_called_once()

def test_gitops_status_iterdir_error():
    """Test error handling in get_gitops_status when iterdir() fails"""
    from python.app.gitops import get_gitops_status
    
    # Mock Path operations - first exists() returns True then iterdir() raises OSError
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.iterdir") as mock_iterdir:
        
        mock_exists.return_value = True
        mock_iterdir.side_effect = OSError("Permission denied")
        
        # Call the function and verify it handles the error
        result = asyncio.run(get_gitops_status())
        
        # Verify result has the expected structure despite the error
        assert result.is_reconciling is not None
        assert result.status in ["active", "inactive"]
        assert isinstance(result.microservices, list)
        assert len(result.microservices) == 0  # Should be empty due to the error

def test_gitops_status_generic_error():
    """Test error handling in get_gitops_status when a generic exception occurs"""
    from python.app.gitops import get_gitops_status
    
    # Mock Path operations - first exists() returns True then iterdir() raises an unexpected error
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.iterdir") as mock_iterdir:
        
        mock_exists.return_value = True
        mock_iterdir.side_effect = Exception("Unexpected error")
        
        # Call the function and verify it handles the error
        result = asyncio.run(get_gitops_status())
        
        # Verify result has the expected structure despite the error
        assert result.is_reconciling is not None
        assert result.status in ["active", "inactive"]
        assert isinstance(result.microservices, list)
        assert len(result.microservices) == 0  # Should be empty due to the error

def test_gitops_status_yaml_error():
    """Test error handling in get_gitops_status when YAML parsing fails"""
    from python.app.gitops import get_gitops_status
    
    # Mock the directory structure and file operations
    with patch("pathlib.Path.exists") as mock_exists, \
         patch("pathlib.Path.iterdir") as mock_iterdir, \
         patch("pathlib.Path.is_dir") as mock_is_dir, \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load") as mock_yaml_load:
        
        # Set up the mocks
        mock_exists.return_value = True
        
        # Create mock namespace and app directories
        namespace_dir = MagicMock()
        namespace_dir.name = "test-namespace"
        namespace_dir.is_dir.return_value = True
        
        app_dir = MagicMock()
        app_dir.name = "test-app"
        app_dir.is_dir.return_value = True
        
        values_file = MagicMock()
        values_file.exists.return_value = True
        
        # Set up directory structure
        mock_iterdir.return_value = [namespace_dir]
        namespace_dir.iterdir.return_value = [app_dir]
        
        # Set up __truediv__ to handle path composition
        def mock_truediv(self, other):
            if other == "values.yaml":
                return values_file
            return MagicMock()
        
        MagicMock.__truediv__ = mock_truediv
        
        # Make YAML parsing fail with YAMLError
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML syntax")
        
        # Call the function
        result = asyncio.run(get_gitops_status())
        
        # Verify microservices list excludes the one with YAML error
        assert len(result.microservices) == 0
        
        # Reset for next test
        mock_yaml_load.reset_mock()
        
        # Test with multiple microservices, only one has YAML error
        app_dir2 = MagicMock()
        app_dir2.name = "valid-app"
        app_dir2.is_dir.return_value = True
        
        values_file2 = MagicMock()
        values_file2.exists.return_value = True
        
        # Update directory structure
        namespace_dir.iterdir.return_value = [app_dir, app_dir2]
        
        # Updated __truediv__ to handle both paths
        def updated_truediv(self, other):
            if other == "values.yaml":
                if self.name == "test-app":
                    return values_file
                else:
                    return values_file2
            return MagicMock()
        
        MagicMock.__truediv__ = updated_truediv
        
        # Make YAML parsing fail only for the first app
        yaml_results = [
            yaml.YAMLError("Invalid YAML syntax"),  # For test-app
            {"image": "valid-image", "tag": "v1.0.0"}  # For valid-app
        ]
        mock_yaml_load.side_effect = yaml_results
        
        # Call the function again
        result = asyncio.run(get_gitops_status())
        
        # Verify only the valid microservice is included
        assert len(result.microservices) == 1
        assert result.microservices[0]["microservices_name"] == "valid-app"