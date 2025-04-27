"""
Test file specifically targeting remaining coverage gaps in app/gitops.py
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import os
import re
import threading
import subprocess
import yaml
from pathlib import Path
from fastapi import HTTPException

from app.gitops import (
    _clone_repository,  # Corrected import name
    _update_repository,
    reconcile_from_git,
    get_gitops_status,
    deploy_microservices,
    sanitize_branch_name,
    sanitize_git_url,
    _apply_configurations_from_git
)

def test_gitops_lines_195_197():
    """Test coverage for lines 195-197 in gitops.py"""
    
    # Mock subprocess.run to simulate command execution
    with patch('subprocess.run') as mock_run:
        # Set up mock to return success for initialization
        mock_run.return_value.returncode = 0
        
        # Create a mock Path that behaves like it exists
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        
        with patch('pathlib.Path', return_value=mock_path):
            # Test the clone repository function with the correct signature
            result = _clone_repository(
                "https://github.com/example/repo.git",
                "/tmp/repo",
                "main"  # branch parameter
            )
            # Function returns None on success
            assert result is None
            # Verify subprocess.run was called
            mock_run.assert_called()

def test_gitops_line_349():
    """Test coverage for line 349 in gitops.py"""
    
    # Mock conditions to hit line 349
    with patch('threading.Thread') as mock_thread, \
         patch('app.gitops._clone_repository', return_value=True), \
         patch('app.gitops._apply_configurations_from_git', return_value=True), \
         patch('app.gitops.set_last_reconciliation_time'):
        
        # Mock the Thread initialization and start method
        mock_thread_instance = MagicMock()
        mock_thread_instance.start.side_effect = RuntimeError("Test error")
        mock_thread.return_value = mock_thread_instance
        
        # Call the function with correct signature (no arguments)
        result = reconcile_from_git()
        
        # Verify reconciliation failed
        assert not result
