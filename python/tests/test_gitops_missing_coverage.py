import importlib
import pytest
import asyncio
import threading
import yaml
import re
from unittest.mock import patch, MagicMock, mock_open
from subprocess import CalledProcessError

def test_import_line_223():
    """Test line 223 - explicitly importing the module to cover 're' import line."""
    # Reload the module to ensure the import lines are executed
    import python.app.gitops
    importlib.reload(python.app.gitops)
    
    # Verify that re module was imported successfully
    assert hasattr(python.app.gitops, 're')
    # Verify other key module components are present
    assert hasattr(python.app.gitops, 'proxy')
    assert hasattr(python.app.gitops, 'logger')

def test_thread_creation_error_lines_341_346():
    """Test lines 341-346 - error handling in thread creation."""
    from python.app.gitops import start_reconciliation_thread
    import python.app.gitops as gitops
    
    # Store original thread reference to restore later
    original_thread = gitops.reconciliation_thread
    
    try:
        # Set thread to None to force new thread creation path
        gitops.reconciliation_thread = None
        
        # Mock threading.Thread to raise an exception
        with patch("threading.Thread") as mock_thread, \
             patch("python.app.gitops.logger.error") as mock_error:
            
            # Make Thread constructor raise an exception
            mock_thread.side_effect = RuntimeError("Thread creation failed")
            
            # Call function and expect exception to be caught and re-raised
            with pytest.raises(Exception) as excinfo:
                start_reconciliation_thread()
            
            # Verify error was logged with correct message
            mock_error.assert_called_once()
            assert "Failed to create reconciliation thread" in mock_error.call_args[0][0]
            
            # Verify the exception contains the expected text
            assert "Failed to start reconciliation thread" in str(excinfo.value)
            
            # Verify thread was not set (reverted to None)
            assert gitops.reconciliation_thread is None
    finally:
        # Restore original thread
        gitops.reconciliation_thread = original_thread

def test_repository_clone_line_461():
    """Test line 461 - clone repository path in reconcile_from_git."""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original state
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Set is_reconciling to False
        gitops.is_reconciling = False
        
        # Mock all dependencies
        with patch("python.app.gitops.get_settings") as mock_get_settings, \
             patch("pathlib.Path.exists") as mock_exists, \
             patch("python.app.gitops._clone_repository") as mock_clone, \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops._apply_configurations_from_git"), \
             patch("python.app.gitops.set_last_reconciliation_time"):
            
            # Configure settings
            mock_settings = MagicMock()
            mock_settings.gitops_repo_path = "/tmp/test-repo"
            mock_settings.gitops_repo_url = "https://github.com/user/repo.git"
            mock_settings.gitops_repo_branch = "main"
            mock_get_settings.return_value = mock_settings
            
            # Configure exists to return False to force cloning
            mock_exists.return_value = False
            
            # Call the function
            reconcile_from_git()
            
            # Verify _clone_repository was called with correct args
            mock_clone.assert_called_once_with(
                mock_settings.gitops_repo_url,
                mock_settings.gitops_repo_path,
                mock_settings.gitops_repo_branch
            )
            
            # Verify _update_repository was not called
            mock_update.assert_not_called()
    finally:
        # Restore original state
        gitops.is_reconciling = original_is_reconciling

def test_lock_acquisition_failure_lines_470_474():
    """Test lines 470-474 - lock acquisition failure in reconcile_from_git."""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original lock and state
    original_lock = gitops.reconciliation_lock
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Create a mock lock that raises RuntimeError when __enter__ is called
        mock_lock = MagicMock()
        mock_lock.__enter__.side_effect = RuntimeError("Failed to acquire lock")
        
        # Replace the lock and reset flag
        gitops.reconciliation_lock = mock_lock
        gitops.is_reconciling = False
        
        # Mock logger to verify error is logged
        with patch("python.app.gitops.logger.error") as mock_error:
            # Call the function
            reconcile_from_git()
            
            # Verify lock acquisition was attempted
            mock_lock.__enter__.assert_called_once()
            
            # Verify error was logged
            mock_error.assert_called_once()
            assert "Failed to acquire reconciliation lock" in mock_error.call_args[0][0]
            
            # Verify is_reconciling is still False
            assert gitops.is_reconciling is False
    finally:
        # Restore original state
        gitops.reconciliation_lock = original_lock
        gitops.is_reconciling = original_is_reconciling

def test_dangerous_url_validation_line_500():
    """Test line 500 - dangerous URL validation in _clone_repository."""
    from python.app.gitops import _clone_repository
    
    # Create mocks
    with patch("os.makedirs"), \
         patch("subprocess.run"), \
         patch("python.app.gitops.sanitize_branch_name", return_value="main"), \
         patch("python.app.gitops.sanitize_git_url") as mock_sanitize_url, \
         patch("python.app.gitops.logger.error") as mock_error:
        
        # Configure sanitize_git_url to return a different value than input
        # This triggers the security check on line 500
        dangerous_url = "https://github.com/user/repo.git; rm -rf /"
        sanitized_url = "https://github.com/user/repo.git"
        mock_sanitize_url.return_value = sanitized_url
        
        # Call function with dangerous URL and expect ValueError
        with pytest.raises(ValueError) as excinfo:
            _clone_repository(dangerous_url, "/tmp/repo", "main")
        
        # Verify error was logged
        mock_error.assert_called_once()
        assert "Potentially dangerous repository URL rejected" in mock_error.call_args[0][0]
        
        # Verify error message
        assert "Invalid repository URL" in str(excinfo.value)

def test_empty_repo_lines_591_592():
    """Test lines 591-592 - empty repository handling in _apply_configurations_from_git."""
    from python.app.gitops import _apply_configurations_from_git
    
    # Create a mock repo path that returns an empty list when iterdir() is called
    mock_repo_path = MagicMock()
    mock_repo_path.iterdir.return_value = []
    
    # Call the function
    _apply_configurations_from_git(mock_repo_path)
    
    # Verify iterdir was called
    mock_repo_path.iterdir.assert_called_once()
    
    # Test with only hidden directories
    mock_repo_path.reset_mock()
    hidden_dir = MagicMock()
    hidden_dir.name = ".git"
    hidden_dir.is_dir.return_value = True
    
    mock_repo_path.iterdir.return_value = [hidden_dir]
    
    # Call the function
    _apply_configurations_from_git(mock_repo_path)
    
    # Verify iterdir was called
    mock_repo_path.iterdir.assert_called_once()

def test_url_sanitization_regex_error_line_640():
    """Test line 640 - regex error handling in sanitize_git_url."""
    from python.app.gitops import sanitize_git_url
    
    # Mock re.sub to raise an exception
    with patch("re.sub") as mock_re_sub, \
         patch("python.app.gitops.logger.warning") as mock_warning:
        
        # Configure re.sub to raise an exception
        mock_re_sub.side_effect = Exception("Regex module error")
        
        # Test with a URL containing dangerous characters
        input_url = "https://github.com/user/repo.git; rm -rf /"
        result = sanitize_git_url(input_url)
        
        # Verify warning was logged
        mock_warning.assert_called_once()
        assert "Error using regex for URL sanitization" in mock_warning.call_args[0][0]
        
        # Verify fallback sanitization was applied
        assert ";" not in result  # Semicolon should be removed
        assert " " not in result  # Spaces should be removed
        
        # Verify slashes in URL paths are preserved (they're valid in URLs)
        assert "https://" in result
        assert "/user/" in result
        
        # Verify result only contains allowed characters
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:@")
        assert all(c in allowed_chars for c in result)