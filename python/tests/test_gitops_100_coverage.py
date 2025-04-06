"""
This file combines targeted test techniques to ensure 100% coverage of gitops.py
"""

import pytest
import importlib
import asyncio
import threading
import yaml
import re
import os
from subprocess import CalledProcessError
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from fastapi import HTTPException

def test_import_to_cover_lines_220_223():
    """Test to cover lines 220-223 - module imports"""
    # Force reload to ensure import lines get executed
    import python.app.gitops
    importlib.reload(python.app.gitops)
    
    # Verify re module was imported
    assert hasattr(python.app.gitops, 're')
    assert re in python.app.gitops.__dict__.values()
    
    # Verify other key imports
    assert hasattr(python.app.gitops, 'logger')
    assert hasattr(python.app.gitops, 'subprocess')
    assert hasattr(python.app.gitops, 'time')

def test_thread_start_error_lines_341_346():
    """Test to cover lines 341-346 - thread start error handling"""
    from python.app.gitops import start_reconciliation_thread
    import python.app.gitops as gitops
    
    # Store original thread
    original_thread = gitops.reconciliation_thread
    
    try:
        # Set thread to None to force creation
        gitops.reconciliation_thread = None
        
        # Create a mock thread that raises on start()
        mock_thread = MagicMock()
        mock_thread_instance = MagicMock()
        mock_thread_instance.start.side_effect = RuntimeError("Failed to start thread")
        mock_thread.return_value = mock_thread_instance
        
        # Apply the mock
        with patch("threading.Thread", mock_thread), \
             patch("python.app.gitops.logger.error") as mock_error, \
             patch("python.app.gitops.logger.info"):
            
            # Call function and expect exception
            with pytest.raises(Exception) as excinfo:
                start_reconciliation_thread()
            
            # Verify error was logged
            assert mock_error.call_count >= 1
            assert "Failed to start reconciliation thread" in str(excinfo.value)
            
            # Verify thread.start was called
            mock_thread_instance.start.assert_called_once()
    finally:
        # Restore original thread
        gitops.reconciliation_thread = original_thread

def test_reconcile_clone_path_line_461():
    """Test to cover line 461 - repository cloning in reconcile_from_git"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original state
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Set up test conditions
        gitops.is_reconciling = False
        
        # Create mocks
        with patch("python.app.gitops.get_settings") as mock_get_settings, \
             patch("pathlib.Path.exists") as mock_exists, \
             patch("python.app.gitops._clone_repository") as mock_clone, \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops._apply_configurations_from_git"), \
             patch("python.app.gitops.set_last_reconciliation_time"), \
             patch("python.app.gitops.logger.info"), \
             patch("python.app.gitops.logger.error"):
            
            # Configure settings
            mock_settings = MagicMock()
            mock_settings.gitops_repo_path = "/tmp/test-repo"
            mock_settings.gitops_repo_url = "https://github.com/test/repo.git"
            mock_settings.gitops_repo_branch = "main"
            mock_get_settings.return_value = mock_settings
            
            # Force repository path to not exist
            mock_exists.return_value = False
            
            # Call the function
            reconcile_from_git()
            
            # Verify clone was called with correct args
            mock_clone.assert_called_once_with(
                mock_settings.gitops_repo_url, 
                mock_settings.gitops_repo_path, 
                mock_settings.gitops_repo_branch
            )
            
            # Verify update was not called
            mock_update.assert_not_called()
    finally:
        # Restore state
        gitops.is_reconciling = original_is_reconciling

def test_lock_acquisition_error_lines_470_474():
    """Test to cover lines 470-474 - lock acquisition error in reconcile_from_git"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original state
    original_lock = gitops.reconciliation_lock
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Create a mock lock that raises on __enter__
        mock_lock = MagicMock()
        mock_lock.__enter__.side_effect = RuntimeError("Lock acquisition failed")
        
        # Install the mock
        gitops.reconciliation_lock = mock_lock
        gitops.is_reconciling = False
        
        # Mock logger
        with patch("python.app.gitops.logger.error") as mock_error:
            # Call the function
            reconcile_from_git()
            
            # Verify lock acquisition was attempted
            mock_lock.__enter__.assert_called_once()
            
            # Verify error was logged
            mock_error.assert_called_once()
            assert "Failed to acquire reconciliation lock" in mock_error.call_args[0][0]
            
            # Verify reconciliation flag remained unchanged
            assert gitops.is_reconciling is False
    finally:
        # Restore state
        gitops.reconciliation_lock = original_lock
        gitops.is_reconciling = original_is_reconciling

def test_dangerous_url_detection_line_500():
    """Test to cover line 500 - dangerous URL detection in _clone_repository"""
    from python.app.gitops import _clone_repository
    
    # Create mocks
    with patch("os.makedirs"), \
         patch("subprocess.run"), \
         patch("python.app.gitops.sanitize_branch_name", return_value="main"), \
         patch("python.app.gitops.sanitize_git_url") as mock_sanitize_url, \
         patch("python.app.gitops.logger.error") as mock_error, \
         patch("python.app.gitops.logger.warning"):
        
        # Set up sanitize_git_url to detect a dangerous URL
        dangerous_url = "https://github.com/user/repo.git; rm -rf /"
        safe_url = "https://github.com/user/repo.git"
        mock_sanitize_url.return_value = safe_url  # Different from input
        
        # Call function
        with pytest.raises(ValueError) as excinfo:
            _clone_repository(dangerous_url, "/tmp/repo", "main")
        
        # Verify error was logged
        mock_error.assert_called_once()
        assert "Potentially dangerous repository URL rejected" in mock_error.call_args[0][0]
        
        # Verify exception message
        assert "Invalid repository URL" in str(excinfo.value)

def test_empty_directory_lines_591_592():
    """Test to cover lines 591-592 - empty directory handling in _apply_configurations_from_git"""
    from python.app.gitops import _apply_configurations_from_git
    
    # Test with empty directory
    mock_repo_path = MagicMock()
    mock_repo_path.iterdir.return_value = []  # Empty directory
    
    # Call function
    _apply_configurations_from_git(mock_repo_path)
    
    # Verify iterdir was called
    mock_repo_path.iterdir.assert_called_once()
    
    # Test with only hidden directories
    mock_repo_path = MagicMock()
    hidden_dir = MagicMock()
    hidden_dir.is_dir.return_value = True
    hidden_dir.name = ".git"  # Hidden directory
    
    mock_repo_path.iterdir.return_value = [hidden_dir]
    
    # Call function
    _apply_configurations_from_git(mock_repo_path)
    
    # Verify iterdir was called
    mock_repo_path.iterdir.assert_called_once()

def test_git_url_sanitization_error_line_640():
    """Test to cover line 640 - error handling in sanitize_git_url"""
    from python.app.gitops import sanitize_git_url
    
    # Force re.sub to raise an exception
    with patch("re.sub") as mock_re_sub, \
         patch("python.app.gitops.logger.warning") as mock_warning:
        
        # Configure re.sub to fail
        mock_re_sub.side_effect = Exception("Regex module failure")
        
        # Call function with a URL that needs sanitization
        url = "https://github.com/user/repo.git; rm -rf /"
        result = sanitize_git_url(url)
        
        # Verify warning was logged
        mock_warning.assert_called_once()
        assert "Error using regex for URL sanitization" in mock_warning.call_args[0][0]
        
        # Verify result only contains allowed characters
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:@")
        assert all(c in allowed_chars for c in result)
        assert ";" not in result