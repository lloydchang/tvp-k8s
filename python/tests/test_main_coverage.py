"""
Test specifically targeting the main function in api/index.py for coverage
"""

import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Make sure system packages are prioritized
if "" in sys.path:
    sys.path.pop(sys.path.index(""))

# Ensure API path is in sys.path
api_path = str(Path(__file__).parent.parent.parent)
if api_path not in sys.path:
    sys.path.insert(0, api_path)

def test_index_main_function():
    """
    Test the main() function in api/index.py to ensure it's covered.
    This function specifically targets line 188 which is not covered.
    """
    # Import the main function directly from the module
    from api.index import main
    
    # Mock uvicorn.run to prevent actually starting a server
    with patch('uvicorn.run') as mock_run:
        # Call the main function
        main()
        
        # Verify the function called uvicorn.run with the correct parameters
        mock_run.assert_called_once_with(
            "api.index:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )