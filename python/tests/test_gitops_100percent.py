"""
Final comprehensive test file to achieve 100% coverage for gitops.py.
This file specifically targets the 18 remaining uncovered lines:
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


def test_nothing_to_commit_inner_handler():
    """Test lines 230-231: Inner handler for 'nothing to commit' in stderr"""
    from python.app.gitops import deploy_application, DeploymentRequest
    import python.app.gitops as gitops
    
    # Setup
    deployment = DeploymentRequest(image="test-image:latest", replicas=2)
    background_tasks = MagicMock()
    
    # Create custom error with the exact text we're looking for
    commit_error = CalledProcessError(
        returncode=1,
        cmd=["git", "commit", "-m", "test commit"]
    )
    commit_error.stderr = "nothing to commit, working tree clean"
    
    # Setup mocks to ensure we hit the specific error path with proper context
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.relative_to", return_value="test/path"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops._update_repository"), \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("python.app.gitops.get_settings") as mock_settings, \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.logger.info") as mock_logger_info:
        
        # Configure settings
        mock_settings.return_value = MagicMock(gitops_repo_path="/test/path")
        
        # Configure run to succeed for the add call, but raise our error for the commit call
        mock_run.side_effect = [MagicMock(), commit_error]
        
        # Run the test
        async def test():
            result = await deploy_application("test-ns", "test-app", deployment, background_tasks)
            # Assert the deployment was "successful" despite the nothing to commit error
            assert result["status"] == "deployment_triggered"
            # Assert the logger was called to record the "nothing to commit" condition
            mock_logger_info.assert_any_call("No changes to commit - values match existing configuration")
            # Verify we didn't continue to the push operation
            assert mock_run.call_count == 2  # Only add and commit were called, not push
            
        asyncio.run(test())


def test_outer_exception_handler_with_stderr():
    """Test lines 274-277: Outer exception handler with stderr attribute"""
    from python.app.gitops import deploy_application, DeploymentRequest
    import python.app.gitops as gitops
    
    # Setup
    deployment = DeploymentRequest(image="test-image:latest", replicas=2)
    background_tasks = MagicMock()
    
    # Create a custom exception with stderr attribute
    class CustomError(CalledProcessError):
        def __init__(self):
            super().__init__(returncode=1, cmd=["git", "add", "."])
            self.stderr = "nothing to commit, working tree clean"
    
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.relative_to", return_value="test/path"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops._update_repository"), \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("python.app.gitops.get_settings") as mock_settings, \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.logger.info") as mock_logger_info:
        
        # Configure settings
        mock_settings.return_value = MagicMock(gitops_repo_path="/test/path")
        
        # Make the run call directly throw our custom exception on the first call (add)
        # This will bypass the inner try/except and go to the outer handler
        mock_run.side_effect = CustomError()
        
        # Run the test
        async def test():
            result = await deploy_application("test-ns", "test-app", deployment, background_tasks)
            # Assert the deployment was "successful" despite the error
            assert result["status"] == "deployment_triggered"
            # Assert the logger recorded the "nothing to commit" info
            mock_logger_info.assert_any_call("No changes to commit - values match existing configuration")
            
        asyncio.run(test())


def test_reconcile_all_exceptions():
    """Test lines 397-402: All exception paths in reconcile_from_git"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Save original state
    original_flag = gitops.is_reconciling
    
    # Helper to create a mock lock
    def create_mock_lock():
        lock = MagicMock()
        lock.__enter__ = MagicMock(return_value=None)
        lock.__exit__ = MagicMock(return_value=None)
        return lock
    
    try:
        # Reset state for testing
        gitops.is_reconciling = False
        
        # Test CalledProcessError case
        with patch("python.app.gitops.reconciliation_lock", create_mock_lock()), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_logger_error:
            
            called_error = CalledProcessError(returncode=1, cmd=["git", "pull"])
            called_error.stderr = "error message"
            mock_update.side_effect = called_error
            
            reconcile_from_git()
            mock_logger_error.assert_any_call(f"Git operation failed: {called_error.cmd} returned {called_error.returncode}: {called_error.stderr}")
        
        # Reset for next test
        gitops.is_reconciling = False
        
        # Test TimeoutExpired case
        with patch("python.app.gitops.reconciliation_lock", create_mock_lock()), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_logger_error:
            
            timeout_error = TimeoutExpired(cmd=["git", "pull"], timeout=30)
            mock_update.side_effect = timeout_error
            
            reconcile_from_git()
            mock_logger_error.assert_any_call(f"Git operation timed out: {timeout_error.cmd} after {timeout_error.timeout} seconds")
        
        # Reset for next test
        gitops.is_reconciling = False
        
        # Test OSError case
        with patch("python.app.gitops.reconciliation_lock", create_mock_lock()), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_logger_error:
            
            os_error = OSError("File system error")
            mock_update.side_effect = os_error
            
            reconcile_from_git()
            mock_logger_error.assert_any_call(f"Filesystem error during reconciliation: {os_error}")
        
        # Reset for next test
        gitops.is_reconciling = False
        
        # Test YAMLError case
        with patch("python.app.gitops.reconciliation_lock", create_mock_lock()), \
             patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops.logger.error") as mock_logger_error:
            
            yaml_error = yaml.YAMLError("Invalid YAML")
            mock_update.side_effect = yaml_error
            
            reconcile_from_git()
            mock_logger_error.assert_any_call(f"YAML parsing error: {yaml_error}")
    
    finally:
        # Restore original state
        gitops.is_reconciling = original_flag


def test_apply_configurations_nested_directories():
    """Test lines 526-530: os.walk for nested directories in _apply_configurations_from_git"""
    from python.app.gitops import _apply_configurations_from_git
    
    # Create a mock repo path with a directory structure
    repo_path = MagicMock()
    namespace_dir = MagicMock()
    app_dir = MagicMock()
    values_file = MagicMock()
    manifests_dir = MagicMock()
    
    # Configure directory structure
    namespace_dir.name = "test-namespace"
    namespace_dir.is_dir.return_value = True
    
    app_dir.name = "test-app"
    app_dir.is_dir.return_value = True
    
    values_file.exists.return_value = True
    
    manifests_dir.exists.return_value = True
    manifests_dir.is_dir.return_value = True
    
    # Fix the __truediv__ lambda to handle multiple arguments correctly
    app_dir.__truediv__ = lambda self, other: values_file if other == "values.yaml" else manifests_dir
    
    # Link the directories
    repo_path.iterdir.return_value = [namespace_dir]
    namespace_dir.iterdir.return_value = [app_dir]
    
    # Create nested directories and YAML files in the walk result
    nested_dirs = [
        ("/repo/test-namespace/test-app/manifests", ["subdir1", "subdir2"], ["file1.yaml", "file2.yaml"]),
        ("/repo/test-namespace/test-app/manifests/subdir1", [], ["nested1.yaml"]),
        ("/repo/test-namespace/test-app/manifests/subdir2", ["subsubdir"], ["nested2.yaml"]),
        ("/repo/test-namespace/test-app/manifests/subdir2/subsubdir", [], ["deep.yaml"])
    ]
    
    # Mock additional required methods to navigate the structure
    manifests_dir.exists.return_value = True
    manifests_dir.is_dir.return_value = True
    manifests_dir.__str__ = lambda self: "/repo/test-namespace/test-app/manifests"
    
    with patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={"image": "test:latest"}), \
         patch("os.walk") as mock_walk, \
         patch("os.path.join", lambda *args: "/".join(args)), \
         patch("python.app.gitops.logger.info"), \
         patch("python.app.gitops.logger.debug"), \
         patch("python.app.gitops.logger.error"), \
         patch("os.path.isdir", return_value=True), \
         patch("kubernetes.client.CoreV1Api"), \
         patch("kubernetes.client.AppsV1Api"), \
         patch("python.app.gitops.get_settings"):
        
        # Set the nested directory structure in the os.walk result
        mock_walk.return_value = nested_dirs
        
        # Call the function
        _apply_configurations_from_git(repo_path)
        
        # Verify os.walk was called with the manifests directory
        mock_walk.assert_called()


def test_sanitize_branch_name_truly_empty():
    """Test line 556: branch name that becomes empty after sanitization"""
    from python.app.gitops import sanitize_branch_name
    
    # Direct test with empty input - should return "main"
    result = sanitize_branch_name("")
    assert result == "main"
    
    # Mock re.sub to return an empty string for all calls
    with patch("re.sub", return_value=""), \
         patch("python.app.gitops.logger.warning"):
        result = sanitize_branch_name("test")
        assert result == "main"
    
    # Test directly with non-alphanumeric input that should produce empty result
    with patch("re.sub", side_effect=lambda p, r, s: ""), \
         patch("python.app.gitops.logger.warning"):
        result = sanitize_branch_name("!@#$%^&*()")
        assert result == "main"


def test_sanitize_git_url_full_fallback():
    """Test lines 647-648, 696: Complete fallback in sanitize_git_url"""
    from python.app.gitops import sanitize_git_url
    
    # Mock re.sub to raise an exception, forcing the fallback path
    with patch("re.sub") as mock_re_sub, \
         patch("python.app.gitops.logger.warning"):
        
        # Make re.sub raise an exception
        mock_re_sub.side_effect = Exception("Regex error")
        
        # Test with URL containing dangerous characters
        url = "git@github.com:user/repo.git; rm -rf /"
        result = sanitize_git_url(url)
        
        # Verify URL was sanitized, but don't check for specific character removals
        # since the implementation may vary
        assert "git@github.com:user/repo.git" in result
        assert ";" not in result
        
        # Directly test behavior by constructing the expected result with same logic
        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:@"
        expected = "".join(c for c in url if c in allowed_chars)
        assert result == expected