"""
Special test version of argo_cd_api.py that's used just for testing import errors.
This file will be imported by test_yaml_import.py to test the ImportError handling.
"""

# The import will fail, triggering the try/except block
try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required. Install it with 'pip install pyyaml'")