"""
Final comprehensive test file to achieve 100% coverage of gitops.py
"""

import pytest
import asyncio
import subprocess
from subprocess import CalledProcessError
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from fastapi import HTTPException
import yaml
import re

def test_deploy_application_nothing_to_commit_exact():
    """Test lines 230-231 and 274-277: nothing to commit exact case handling"""
    from python.app.gitops import deploy_application, DeploymentRequest
    import python.app.gitops as gitops
    
    # Create deployment request
    deployment = DeploymentRequest(
        image="test-image:latest",
        replicas=2
    )
    
    # Create background_tasks mock
    background_tasks = MagicMock()
    
    # Create CalledProcessError that has the exact "nothing to commit" error
    commit_error = CalledProcessError(
        returncode=1,
        cmd=["git", "commit", "-m", "Update test-namespace/test-app deployment"]
    )
    commit_error.stderr = "nothing to commit, working tree clean"
    
    # Setup patches to precisely target the execution path
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops._update_repository"), \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.get_settings") as mock_get_settings, \
         patch("python.app.gitops.logger.info"), \
         patch("python.app.gitops.logger.error"):
        
        # Setup settings
        mock_settings_value = MagicMock()
        mock_settings_value.gitops_repo_path = "/tmp/kubernetes-apps"
        mock_get_settings.return_value = mock_settings_value
        
        # Configure the mock to raise our specific error
        mock_run.side_effect = [
            MagicMock(),    # First call (git add) succeeds
            commit_error,   # Second call (git commit) raises our error
        ]
        
        # Execute the test
        async def test():
            result = await deploy_application(
                "test-namespace",
                "test-app",
                deployment,
                background_tasks
            )
            
            # Verify function succeeds and returns the expected result
            assert result["status"] == "deployment_triggered"
            assert "no changes" in result["message"].lower()
            
            # Verify reconciliation was triggered
            background_tasks.add_task.assert_called_once_with(gitops.reconcile_from_git)
        
        # Run the test
        asyncio.run(test())

def test_outer_exception_handler_nothing_to_commit():
    """Test lines 274-277: "nothing to commit" in outer exception handler"""
    from python.app.gitops import deploy_application, DeploymentRequest
    import python.app.gitops as gitops
    
    # Create deployment request
    deployment = DeploymentRequest(
        image="test-image:latest",
        replicas=2
    )
    
    # Create background_tasks mock
    background_tasks = MagicMock()
    
    # Create a custom exception class with stderr attribute
    class CustomProcessError(Exception):
        def __init__(self, stderr):
            self.stderr = stderr
            super().__init__(stderr)
    
    # Setup patches
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.mkdir"), \
         patch("builtins.open", mock_open()), \
         patch("yaml.safe_load", return_value={}), \
         patch("yaml.safe_dump"), \
         patch("python.app.gitops.get_settings") as mock_get_settings, \
         patch("subprocess.run") as mock_run, \
         patch("python.app.gitops.reconcile_from_git"), \
         patch("python.app.gitops.logger.info"), \
         patch("python.app.gitops.logger.error"), \
         patch("python.app.gitops.logger.exception"):
        
        # Configure settings
        mock_settings_value = MagicMock()
        mock_settings_value.gitops_repo_path = "/tmp/kubernetes-apps"
        mock_get_settings.return_value = mock_settings_value
        
        # Configure mock_run to fail with a CalledProcessError
        error = CustomProcessError("nothing to commit, working tree clean")
        mock_run.side_effect = error
        
        # Execute test
        async def test():
            result = await deploy_application(
                "test-namespace",
                "test-app",
                deployment,
                background_tasks
            )
            
            # Verify it succeeds and returns expected result
            assert result["status"] == "deployment_triggered"
            assert "no changes" in result["message"].lower()
            
            # Verify reconciliation was triggered
            background_tasks.add_task.assert_called_once_with(gitops.reconcile_from_git)
        
        # Run the test
        asyncio.run(test())

def test_reconcile_errors_specific():
    """Test lines 397-402: specific error handling in reconcile_from_git"""
    from python.app.gitops import reconcile_from_git
    import python.app.gitops as gitops
    
    # Store original state
    original_is_reconciling = gitops.is_reconciling
    
    try:
        # Set up for testing
        gitops.is_reconciling = False
        
        # Create mock for git operations that will raise specific errors
        with patch("pathlib.Path.exists", return_value=True), \
             patch("python.app.gitops._update_repository") as mock_update, \
             patch("python.app.gitops._apply_configurations_from_git"), \
             patch("python.app.gitops.set_last_reconciliation_time"), \
             patch("python.app.gitops.get_settings"), \
             patch("python.app.gitops.logger.error"), \
             patch("python.app.gitops.logger.exception"):
            
            # Test each specific error type that should be caught
            
            # 1. Test TimeoutExpired
            timeout_error = subprocess.TimeoutExpired(cmd=["git", "pull"], timeout=30)
            mock_update.side_effect = timeout_error
            reconcile_from_git()  # Should handle the error and continue
            
            # 2. Test CalledProcessError
            called_error = CalledProcessError(
                returncode=1, 
                cmd=["git", "pull"]
            )
            called_error.stderr = "error: failed to pull"
            mock_update.side_effect = called_error
            reconcile_from_git()  # Should handle the error and continue
            
            # 3. Test YAML error
            yaml_error = yaml.YAMLError("Invalid YAML format")
            mock_update.side_effect = yaml_error
            reconcile_from_git()  # Should handle the error and continue
    finally:
        # Restore original state
        gitops.is_reconciling = original_is_reconciling

def test_apply_configurations_nested_dirs():
    """Test lines 526-530: nested directories in _apply_configurations_from_git"""
    from python.app.gitops import _apply_configurations_from_git
    
    # Create a mock repo path with nested structure
    mock_repo_path = MagicMock()
    
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
    
    # Create manifests dir
    manifests_dir = MagicMock()
    manifests_dir.exists.return_value = True
    manifests_dir.is_dir.return_value = True
    
    # Setup directory hierarchy
    mock_repo_path.iterdir.return_value = [namespace_dir]
    namespace_dir.iterdir.return_value = [app_dir]
    
    # Configure special path joining with __truediv__
    def mock_truediv(self, other):
        if other == "values.yaml":
            return values_file
        elif other == "manifests":
            return manifests_dir
        return MagicMock()
    
    app_dir.__truediv__ = mock_truediv
    
    # Setup os.walk patch to return nested directories with YAML files
    with patch("builtins.open", mock_open(read_data="{}")), \
         patch("yaml.safe_load", return_value={}), \
         patch("os.walk") as mock_walk, \
         patch("os.path.join", lambda *args: "/".join(args)), \
         patch("python.app.gitops.logger.debug"), \
         patch("python.app.gitops.logger.error"):
        
        # Configure os.walk to return a nested directory structure
        mock_walk.return_value = [
            ("/manifests", ["subdir"], ["config1.yaml"]),
            ("/manifests/subdir", [], ["config2.yaml", "config3.yml"])
        ]
        
        # Call the function
        _apply_configurations_from_git(mock_repo_path)

def test_empty_branch_name_after_sanitization():
    """Test line 556: branch name that becomes empty after sanitization"""
    from python.app.gitops import sanitize_branch_name
    
    # Test with input that becomes empty after sanitization
    with patch("re.sub") as mock_re_sub:
        # Configure re.sub to return empty strings
        mock_re_sub.return_value = ""
        
        # Call the function and verify it returns "main" for empty result
        result = sanitize_branch_name("...")
        assert result == "main"
    
    # Test directly with characters that should be removed
    with patch("re.sub", side_effect=[
            "",  # First call to remove path traversal
            "",  # Second call to replace slashes
            "",  # Third call to replace dangerous chars
        ]):
        result = sanitize_branch_name("../../../etc/passwd")
        assert result == "main"

def test_git_url_sanitize_fallback():
    """Test lines 647-648, 696: fallback in sanitize_git_url"""
    from python.app.gitops import sanitize_git_url
    
    # Test with regex failing
    with patch("re.sub") as mock_re_sub:
        # Make re.sub raise an exception
        mock_re_sub.side_effect = Exception("Regex failure")
        
        # Call function with dangerous URL that should be sanitized
        url = "https://github.com/user/repo.git; rm -rf /"
        result = sanitize_git_url(url)
        
        # Verify dangerous characters were removed
        assert ";" not in result
        assert " " not in result
        assert "-" not in result  # "rm" split becomes "r" "f"
        assert "rm" not in result.replace("-", "")  # Ensure "rm" is gone even after hyphen removal
        assert "https" in result
        assert "github.com" in result