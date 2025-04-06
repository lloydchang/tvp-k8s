"""
Direct line-by-line test targeting specifically and only the uncovered lines in gitops.py.
This file is focused on achieving 100% code coverage by precisely targeting:
- Lines 230-231: "nothing to commit" handling
- Lines 274-277: Error handling in deploy_application
- Lines 397-402: Repository operations in reconcile_from_git
- Lines 526-530: Nested directory handling in _apply_configurations_from_git
- Line 556: Empty branch name handling in sanitize_branch_name
- Lines 647-648, 696: Fallback sanitization in sanitize_git_url
"""

import asyncio
import os
import re
import subprocess
import threading
import yaml
from fastapi import HTTPException, BackgroundTasks
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired
from unittest.mock import MagicMock, patch, mock_open, PropertyMock
import pytest
from typing import Dict, Any


def test_line_230_231_nothing_to_commit_inner_path():
    """Directly test lines 230-231: Inner try/except 'nothing to commit' handling"""
    from python.app.gitops import deploy_application, DeploymentRequest
    
    # Setup test data
    deployment = DeploymentRequest(image="test-image:v1.0", replicas=2)
    background_tasks = MagicMock()
    
    # Create a specific CalledProcessError with stderr containing "nothing to commit"
    git_error = CalledProcessError(1, ["git", "commit"])
    git_error.stderr = "nothing to commit, working tree clean"
    
    # Setup all necessary mocks
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.relative_to", return_value="test/path"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops._update_repository"), \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("python.app.gitops.get_settings") as mock_get_settings, \
         patch("python.app.gitops.logger.info") as mock_logger_info, \
         patch("subprocess.run") as mock_run:
        
        # Configure mock settings
        mock_settings_value = MagicMock()
        mock_settings_value.gitops_repo_path = "/tmp/repo"
        mock_get_settings.return_value = mock_settings_value
        
        # Configure subprocess.run to return normal MagicMock for first call (add)
        # and raise our custom error for second call (commit)
        mock_run.side_effect = [MagicMock(), git_error]
        
        # Run the test asynchronously
        async def run_test():
            # Call the function
            result = await deploy_application(
                "test-namespace", 
                "test-app", 
                deployment, 
                background_tasks
            )
            
            # Verify it handled "nothing to commit" correctly
            assert result["status"] == "deployment_triggered"
            assert "test-app" in result["message"]
            assert "test-namespace" in result["message"]
            
            # Verify logger was called with the expected message
            mock_logger_info.assert_any_call("No changes to commit - values match existing configuration")
            
            # Verify we called subprocess.run exactly twice (add and commit, not push)
            assert mock_run.call_count == 2
        
        # Run the async test
        asyncio.run(run_test())


def test_line_274_277_error_handler_with_stderr():
    """Directly test lines 274-277: Deploy application outer exception handler with stderr"""
    from python.app.gitops import deploy_application, DeploymentRequest
    import python.app.gitops as gitops
    
    # Setup test data
    deployment = DeploymentRequest(image="test-image:v1.0", replicas=2)
    background_tasks = MagicMock()
    
    # Create a custom exception with stderr attribute
    class TestException(Exception):
        def __init__(self):
            self.stderr = "nothing to commit, working tree clean"
    
    # Setup mocks
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.relative_to", return_value="test/path"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops.get_settings") as mock_get_settings, \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("python.app.gitops.logger.info") as mock_logger_info:
        
        # Configure settings
        mock_settings_value = MagicMock()
        mock_settings_value.gitops_repo_path = "/tmp/repo"
        mock_get_settings.return_value = mock_settings_value
        
        # Create the mocked exception and make run raise it
        test_exception = TestException()
        mock_run.side_effect = test_exception
        
        # Run the test asynchronously
        async def run_test():
            # Call the function
            result = await deploy_application(
                "test-namespace", 
                "test-app", 
                deployment, 
                background_tasks
            )
            
            # Verify it handled the exception correctly
            assert result["status"] == "deployment_triggered"
            assert "(no changes)" in result["message"]
            
            # Verify reconciliation was triggered
            background_tasks.add_task.assert_called_once_with(gitops.reconcile_from_git)
            
            # Verify logger was called
            mock_logger_info.assert_any_call("No changes to commit detected in error message - values match existing configuration")
        
        # Run the async test
        asyncio.run(run_test())


def test_line_397_402_reconcile_exceptions():
    """Directly test lines 397-402: All exception paths in reconcile_from_git"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Save and restore original state
    original_flag = gitops.is_reconciling
    
    try:
        # Create a mock lock that works properly
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=None)
        
        # Setup test environment
        gitops.is_reconciling = False
        
        # Test CalledProcessError case
        with patch("python.app.gitops.reconciliation_lock", mock_lock), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_error:
            
            # Create CalledProcessError with stderr
            cmd_error = CalledProcessError(returncode=1, cmd=["git", "pull"])
            cmd_error.stderr = "error message"
            mock_update.side_effect = cmd_error
            
            # Call function
            reconcile_from_git()
            
            # Verify exception was handled correctly
            error_msg = f"Git operation failed: {cmd_error.cmd} returned {cmd_error.returncode}: {cmd_error.stderr}"
            mock_error.assert_any_call(error_msg)
            
        # Test TimeoutExpired case
        gitops.is_reconciling = False
        with patch("python.app.gitops.reconciliation_lock", mock_lock), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_error:
            
            # Create TimeoutExpired exception
            timeout_error = TimeoutExpired(cmd=["git", "pull"], timeout=30)
            mock_update.side_effect = timeout_error
            
            # Call function
            reconcile_from_git()
            
            # Verify exception was handled correctly
            error_msg = f"Git operation timed out: {timeout_error.cmd} after {timeout_error.timeout} seconds"
            mock_error.assert_any_call(error_msg)
            
        # Test OSError case
        gitops.is_reconciling = False
        with patch("python.app.gitops.reconciliation_lock", mock_lock), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_error:
            
            # Create OSError
            os_error = OSError("Filesystem error")
            mock_update.side_effect = os_error
            
            # Call function
            reconcile_from_git()
            
            # Verify exception was handled correctly
            error_msg = f"Filesystem error during reconciliation: {os_error}"
            mock_error.assert_any_call(error_msg)
            
        # Test YAMLError case
        gitops.is_reconciling = False
        with patch("python.app.gitops.reconciliation_lock", mock_lock), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_error:
            
            # Create YAMLError
            yaml_error = yaml.YAMLError("Invalid YAML")
            mock_update.side_effect = yaml_error
            
            # Call function
            reconcile_from_git()
            
            # Verify exception was handled correctly
            error_msg = f"YAML parsing error: {yaml_error}"
            mock_error.assert_any_call(error_msg)
    
    finally:
        # Restore original state
        gitops.is_reconciling = original_flag


def test_line_526_530_nested_directories():
    """Directly test lines 526-530: os.walk in _apply_configurations_from_git"""
    from python.app.gitops import _apply_configurations_from_git
    
    # Create a mock directory structure
    repo_path = MagicMock()
    
    # Setup nested mock directories and files
    namespace_dir = MagicMock()
    app_dir = MagicMock()
    values_file = MagicMock()
    manifests_dir = MagicMock()
    
    # Configure the mocks
    namespace_dir.name = "test-namespace"
    namespace_dir.is_dir.return_value = True
    app_dir.name = "test-app"
    app_dir.is_dir.return_value = True
    values_file.exists.return_value = True
    manifests_dir.exists.return_value = True
    manifests_dir.is_dir.return_value = True
    
    # Configure directory structure
    repo_path.iterdir.return_value = [namespace_dir]
    namespace_dir.iterdir.return_value = [app_dir]
    app_dir.__truediv__ = lambda x: values_file if x == "values.yaml" else manifests_dir
    manifests_dir.__str__ = lambda x: "/mock/path/to/manifests"
    
    # Define file structure for os.walk to return
    walk_result = [
        ("/mock/path/to/manifests", ["subdir1", "subdir2"], ["file1.yaml", "file2.yml"]),
        ("/mock/path/to/manifests/subdir1", [], ["nested1.yaml"]),
        ("/mock/path/to/manifests/subdir2", ["subsubdir"], ["nested2.yml"]),
        ("/mock/path/to/manifests/subdir2/subsubdir", [], ["deep.yaml"])
    ]
    
    # Setup mocks
    with patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={"key": "value"}), \
         patch("os.walk", return_value=walk_result), \
         patch("os.path.join", lambda *args: "/".join(args)), \
         patch("python.app.gitops.logger.info"), \
         patch("python.app.gitops.logger.debug"), \
         patch("python.app.gitops.logger.error"):
        
        # Call the function being tested
        _apply_configurations_from_git(repo_path)


def test_line_556_empty_branch_name():
    """Directly test line 556: Empty result in sanitize_branch_name"""
    from python.app.gitops import sanitize_branch_name
    
    # Test with empty input
    assert sanitize_branch_name("") == "main"
    
    # Test with None input 
    assert sanitize_branch_name(None) == "main"
    
    # Test with input that becomes empty after sanitization
    with patch("re.sub") as mock_re_sub:
        # Make re.sub always return empty string
        mock_re_sub.return_value = ""
        
        # Test the function - should return "main" for empty result
        result = sanitize_branch_name("...")
        assert result == "main"
    
    # Another approach that tests the actual empty branch after sanitization
    # by forcing all regex operations to return empty strings
    with patch("re.sub", side_effect=lambda *args, **kwargs: ""):
        result = sanitize_branch_name("any-input")
        assert result == "main"


def test_line_647_648_696_url_sanitization_fallback():
    """Directly test lines 647-648, 696: URL sanitization fallback"""
    from python.app.gitops import sanitize_git_url
    
    # Test with re.sub raising exception
    with patch("re.sub") as mock_re_sub, \
         patch("python.app.gitops.logger.warning") as mock_warning:
        
        # Make re.sub raise an exception
        mock_re_sub.side_effect = Exception("Regex error")
        
        # Test with a dangerous URL that should trigger fallback sanitization
        url = "https://github.com/user/repo.git; rm -rf /"
        result = sanitize_git_url(url)
        
        # Verify fallback was used
        mock_warning.assert_called_once()
        
        # Verify result contains only allowed characters
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:@"
        for char in result:
            assert char in allowed_chars
            
        # Verify dangerous characters were removed
        assert ";" not in result
        assert " " not in result