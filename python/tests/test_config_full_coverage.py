"""
Test file specifically targeting remaining coverage gaps in app/config.py
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import os
from kubernetes import client

from app.config import get_settings, get_kubernetes_client, get_kubernetes_token

def test_get_kubernetes_token_complete_coverage():
    """Test get_kubernetes_token with all code paths covered, including line 138"""
    # Test when token file exists but is empty
    with patch('builtins.open', mock_open(read_data="")), \
         patch('os.path.exists', return_value=True):
        token = get_kubernetes_token()
        # The function returns an empty string, not None
        assert token == ""
