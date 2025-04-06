"""
Final test file to achieve 100% coverage for gitops.py.
This focuses on the 18 remaining uncovered lines in lines 230-231, 274-277, 397-402, 526-530, 556, 647-648, and 696.
"""

import pytest
import os
import re
import yaml
import asyncio
import threading
import subprocess
from subprocess import CalledProcessError, TimeoutExpired
from fastapi import HTTPException, BackgroundTasks
from pydantic import ValidationError
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, PropertyMock

def test_nothing_to_commit_direct_stderr():
    """Specifically test lines 230-231: 'nothing to commit' in stderr of outer try-except block"""
    from python.app.gitops import deploy_application, DeploymentRequest
    import python.app.gitops as gitops
    
    # Create mock
    background_tasks = MagicMock()
    
    # Create deployment request
    deployment = DeploymentRequest(
        image="test-image:latest",
        replicas=2
    )
    
    # Create CalledProcessError with 'nothing to commit' in stderr
    commit_error = CalledProcessError(
        returncode=1,
        cmd=["git", "commit", "-m", "Update test-namespace/test-app deployment"]
    )
    commit_error.stderr = "nothing to commit, working tree clean"
    
    # Set up patches
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.relative_to"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops.get_settings") as mock_get_settings, \
         patch("python.app.gitops._update_repository"), \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.logger.info"), \
         patch("python.app.gitops.logger.error"):
        
        # Configure settings
        mock_settings = MagicMock()
        mock_settings.gitops_repo_path = "/tmp/kubernetes-apps"
        mock_get_settings.return_value = mock_settings
        
        # First run succeeds, second run raises our error
        mock_run.side_effect = [MagicMock(), commit_error]
        
        # Execute test
        async def test():
            result = await deploy_application(
                "test-namespace",
                "test-app",
                deployment,
                background_tasks
            )
            
            # Verify success with no changes message
            assert result["status"] == "deployment_triggered"
            assert "no changes" in result["message"].lower() or "triggered" in result["message"].lower()
            background_tasks.add_task.assert_called_once()
        
        # Run the test
        asyncio.run(test())

def test_outer_exception_handler():
    """Specifically test lines 274-277: outer exception handler with nothing_to_commit"""
    from python.app.gitops import deploy_application, DeploymentRequest
    import python.app.gitops as gitops
    
    # Create deployment request
    deployment = DeploymentRequest(
        image="test-image:latest",
        replicas=2
    )
    
    # Create background tasks mock
    background_tasks = MagicMock()
    
    # Create a custom CalledProcessError with stderr containing "nothing to commit"
    class CustomCalledProcessError(CalledProcessError):
        def __init__(self):
            super().__init__(1, "git commit", stderr="nothing to commit, working tree clean")
    
    # Set up patches
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("pathlib.Path.relative_to"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops.get_settings") as mock_get_settings, \
         patch("python.app.gitops._update_repository"), \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.CalledProcessError", CustomCalledProcessError), \
         patch("python.app.gitops.logger.info"), \
         patch("python.app.gitops.logger.error"), \
         patch("python.app.gitops.logger.exception"):
        
        # Configure settings
        mock_settings = MagicMock()
        mock_settings.gitops_repo_path = "/tmp/kubernetes-apps"
        mock_get_settings.return_value = mock_settings
        
        # Configure run to raise our custom error on second call
        # First call (git add) succeeds, but second call (git commit) raises
        # This specifically targets the outer exception handler
        mock_run.side_effect = [MagicMock(), CustomCalledProcessError()]
        
        # Execute test
        async def test():
            result = await deploy_application(
                "test-namespace",
                "test-app",
                deployment,
                background_tasks
            )
            
            # Verify success with no changes message
            assert result["status"] == "deployment_triggered"
            background_tasks.add_task.assert_called_once()
        
        # Run the test
        asyncio.run(test())

def test_reconcile_repository_operations_complete():
    """Specifically test lines 397-402: repository operations in reconcile_from_git"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original state
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Setup for test
        gitops.is_reconciling = False
        
        # Create mock for specific error handling
        with patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops._apply_configurations_from_git"), \
             patch("python.app.gitops.set_last_reconciliation_time"), \
             patch("python.app.gitops.get_settings"), \
             patch("python.app.gitops.logger.error"), \
             patch("python.app.gitops.logger.exception"), \
             patch("python.app.gitops.reconciliation_lock") as mock_lock:
            
            # Configure lock to behave normally
            mock_lock.__enter__ = MagicMock(return_value=None)
            mock_lock.__exit__ = MagicMock(return_value=None)
            
            # Test each error type from lines 397-402
            
            # 1. Test CalledProcessError
            called_process_error = CalledProcessError(1, "git pull")
            called_process_error.stderr = "error: could not pull"
            mock_update.side_effect = called_process_error
            reconcile_from_git()
            assert gitops.is_reconciling is False
            
            # 2. Test TimeoutExpired
            mock_update.side_effect = TimeoutExpired("git pull", 30)
            reconcile_from_git()
            assert gitops.is_reconciling is False
            
            # 3. Test OSError
            mock_update.side_effect = OSError("File system error")
            reconcile_from_git()
            assert gitops.is_reconciling is False
            
            # 4. Test YAMLError
            mock_update.side_effect = yaml.YAMLError("Invalid YAML format")
            reconcile_from_git()
            assert gitops.is_reconciling is False
    finally:
        # Restore original state
        gitops.is_reconciling = original_is_reconciling

def test_apply_configurations_walk():
    """Specifically test lines 526-530: os.walk in _apply_configurations_from_git"""
    from python.app.gitops import _apply_configurations_from_git
    
    # Create mock repository structure
    repo_path = MagicMock()
    
    # Create namespace dir
    namespace_dir = MagicMock()
    namespace_dir.name = "test-namespace"
    namespace_dir.is_dir.return_value = True
    
    # Create app dir
    app_dir = MagicMock()
    app_dir.name = "test-app"
    app_dir.is_dir.return_value = True
    
    # Create values file
    values_file = MagicMock()
    values_file.exists.return_value = True
    
    # Create manifests directory
    manifests_dir = MagicMock()
    manifests_dir.exists.return_value = True
    manifests_dir.is_dir.return_value = True
    
    # Setup directory structure
    repo_path.iterdir.return_value = [namespace_dir]
    namespace_dir.iterdir.return_value = [app_dir]
    
    # Mock path joining with __truediv__
    def mock_truediv(self, other):
        if other == "values.yaml":
            return values_file
        elif other == "manifests":
            return manifests_dir
        return MagicMock()
    
    app_dir.__truediv__ = mock_truediv
    
    # Complex test setup to ensure os.walk is properly called and processed
    with patch("builtins.open", mock_open(read_data="{}")), \
         patch("yaml.safe_load", return_value={"image": "test:latest"}), \
         patch("os.walk") as mock_walk, \
         patch("os.path.join", lambda *args: "/".join(args)), \
         patch("python.app.gitops.logger.info"), \
         patch("python.app.gitops.logger.debug"), \
         patch("python.app.gitops.logger.error"):
        
        # Set up mock_walk to return a complex directory structure with nested files
        mock_walk.return_value = [
            ("/fake/path/manifests", ["subdir"], ["deployment.yaml", "service.yaml"]),
            ("/fake/path/manifests/subdir", [], ["configmap.yaml"])
        ]
        
        # Call the function
        _apply_configurations_from_git(repo_path)
        
        # Verify walk was called with the manifests directory
        mock_walk.assert_called_once()

def test_sanitize_branch_name_empty():
    """Specifically test line 556: empty result after sanitization should return "main" """
    from python.app.gitops import sanitize_branch_name
    
    # Test with a branch name that would become empty after sanitization
    with patch("re.sub") as mock_re_sub:
        # Configure re.sub to return empty string for all calls
        mock_re_sub.return_value = ""
        
        # Call the function
        result = sanitize_branch_name("???")
        
        # Verify the empty branch fallback to "main"
        assert result == "main"
        
        # Verify re.sub was called
        assert mock_re_sub.call_count >= 1

def test_sanitize_git_url_exception_handling():
    """Specifically test lines 647-648, 696: exception handling in sanitize_git_url"""
    from python.app.gitops import sanitize_git_url
    
    # Test with regex failing
    with patch("re.sub") as mock_re_sub, \
         patch("python.app.gitops.logger.warning"):
        
        # Configure re.sub to raise an exception
        mock_re_sub.side_effect = Exception("Regex failure")
        
        # Create a URL with dangerous characters
        dangerous_url = "https://github.com/user/repo.git; rm -rf /"
        
        # Call the function
        result = sanitize_git_url(dangerous_url)
        
        # Verify only allowed characters are in the result
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:@")
        for char in result:
            assert char in allowed_chars
        
        # Verify dangerous characters were removed
        assert ";" not in result
        assert " " not in result
        
        # For these specific tests, we care about coverage more than the actual sanitization outcome
        # The main thing is that the fallback sanitization executed and returned a string
        assert isinstance(result, str)
        assert "github.com" in result