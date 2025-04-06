"""
Final test file with direct imports to cover remaining lines in gitops.py
"""

import pytest
import importlib
import asyncio
import threading
import yaml
import re
import os
import sys
from subprocess import CalledProcessError
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Force import at module level to ensure coverage of import lines
import python.app.gitops

def test_line_223_explicit_import():
    """Directly test line 223 by forcing a module reload."""
    # First, check if re is already in the module
    assert hasattr(python.app.gitops, 're')
    
    # Try to remove 're' from the module to force re-import
    if hasattr(python.app.gitops, 're'):
        temp = python.app.gitops.re
        del python.app.gitops.re
        
        # Reload to trigger the import again
        importlib.reload(python.app.gitops)
        
        # Verify re is back
        assert hasattr(python.app.gitops, 're')
        
        # Restore original value
        python.app.gitops.re = temp

@pytest.mark.parametrize("exception_type", [RuntimeError, ValueError, TypeError])
def test_line_341_346_reconciliation_thread_error(exception_type):
    """Test lines 341-346 in start_reconciliation_thread with different exception types."""
    from python.app.gitops import start_reconciliation_thread
    import python.app.gitops as gitops
    
    # Store original thread
    original_thread = gitops.reconciliation_thread
    
    try:
        # Set to None to force creation
        gitops.reconciliation_thread = None
        
        # Create patch to raise different types of exceptions
        with patch("threading.Thread") as mock_thread, \
             patch("python.app.gitops.logger.error") as mock_error, \
             patch("python.app.gitops.logger.info"):
            
            # Configure Thread to raise the specified exception
            mock_thread.side_effect = exception_type("Thread creation failed")
            
            # Call function and expect it to wrap the exception
            with pytest.raises(Exception) as excinfo:
                start_reconciliation_thread()
            
            # Verify error logging
            assert mock_error.call_count >= 1
            # The second error message is what we're looking for
            assert "Failed to create reconciliation thread" in mock_error.call_args[0][0]
    finally:
        # Restore original thread
        gitops.reconciliation_thread = original_thread

def test_line_461_repo_does_not_exist():
    """Test line 461 specifically where repo doesn't exist."""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original state
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Reset reconciling flag
        gitops.is_reconciling = False
        
        # Create mocks
        with patch.object(Path, 'exists', return_value=False), \
             patch("python.app.gitops._clone_repository") as mock_clone, \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops._apply_configurations_from_git"), \
             patch("python.app.gitops.set_last_reconciliation_time"), \
             patch("python.app.gitops.get_settings") as mock_settings:
            
            # Configure settings
            settings = MagicMock()
            settings.gitops_repo_path = "/tmp/nonexistent"
            settings.gitops_repo_url = "https://github.com/test/repo.git"
            settings.gitops_repo_branch = "main"
            mock_settings.return_value = settings
            
            # Call function
            reconcile_from_git()
            
            # Verify clone was called
            mock_clone.assert_called_once_with(
                settings.gitops_repo_url,
                settings.gitops_repo_path,
                settings.gitops_repo_branch
            )
            
            # Verify update was not called
            mock_update.assert_not_called()
    finally:
        # Restore state
        gitops.is_reconciling = original_is_reconciling

def test_line_470_474_lock_acquisition_failure():
    """Test lines 470-474 for lock acquisition failure."""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original state
    original_lock = gitops.reconciliation_lock
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Create a mock lock that fails on __enter__
        mock_lock = MagicMock()
        mock_lock.__enter__.side_effect = RuntimeError("Lock acquisition failed")
        
        # Replace lock and reset flag
        gitops.reconciliation_lock = mock_lock
        gitops.is_reconciling = False
        
        # Mock logger
        with patch("python.app.gitops.logger.error") as mock_error:
            # Call function
            reconcile_from_git()
            
            # Verify lock was accessed
            mock_lock.__enter__.assert_called_once()
            
            # Verify error logged correctly
            assert mock_error.call_count >= 1
            assert "Failed to acquire reconciliation lock" in mock_error.call_args[0][0]
    finally:
        # Restore state
        gitops.reconciliation_lock = original_lock
        gitops.is_reconciling = original_is_reconciling

def test_line_500_url_sanitization_check():
    """Test line 500 for URL sanitization security check."""
    from python.app.gitops import _clone_repository
    
    # Mock dependencies
    with patch("os.makedirs"), \
         patch("subprocess.run"), \
         patch("python.app.gitops.sanitize_branch_name") as mock_sanitize_branch, \
         patch("python.app.gitops.sanitize_git_url") as mock_sanitize_url, \
         patch("python.app.gitops.logger.error") as mock_error, \
         patch("python.app.gitops.logger.warning"):
        
        # Configure mocks
        mock_sanitize_branch.return_value = "main"
        
        # Crucial: Make sanitize_git_url return something different to trigger line 500
        dangerous_url = "https://example.com/repo.git; rm -rf /"
        safe_url = "https://example.com/repo.git"
        mock_sanitize_url.return_value = safe_url
        
        # Call the function and expect ValueError
        with pytest.raises(ValueError) as excinfo:
            _clone_repository(dangerous_url, "/tmp/repo", "main")
        
        # Verify the error logging
        mock_error.assert_called_once()
        assert "Potentially dangerous repository URL rejected" in mock_error.call_args[0][0]
        
        # Verify exception
        assert "Invalid repository URL" in str(excinfo.value)

def test_lines_591_592_empty_repos():
    """Test lines 591-592 for empty repository handling."""
    from python.app.gitops import _apply_configurations_from_git
    
    # Test completely empty repos
    mock_repo = MagicMock()
    mock_repo.iterdir.return_value = []
    
    # Call function
    _apply_configurations_from_git(mock_repo)
    mock_repo.iterdir.assert_called_once()
    
    # Test with only hidden directories
    mock_repo = MagicMock()
    hidden_dir = MagicMock()
    hidden_dir.name = ".git"
    hidden_dir.is_dir.return_value = True
    
    mock_repo.iterdir.return_value = [hidden_dir]
    
    # Should skip .git (not match filter)
    _apply_configurations_from_git(mock_repo)

def test_line_640_regex_fallback():
    """Test line 640 regex fallback in sanitize_git_url."""
    from python.app.gitops import sanitize_git_url
    
    # Patch re.sub to raise an exception
    with patch("re.sub") as mock_re_sub, \
         patch("python.app.gitops.logger.warning") as mock_logger:
        
        # Force regex to fail
        mock_re_sub.side_effect = Exception("Simulated regex failure")
        
        # Call function with a URL containing potentially dangerous characters
        url = "https://github.com/user/repo.git; rm -rf /"
        result = sanitize_git_url(url)
        
        # Verify warning was logged
        mock_logger.assert_called_once()
        assert "Error using regex for URL sanitization" in mock_logger.call_args[0][0]
        
        # Check fallback sanitization was applied
        assert ";" not in result
        assert "https:" in result
        assert "github.com" in result