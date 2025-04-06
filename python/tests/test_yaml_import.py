import pytest
import sys
import importlib
from unittest.mock import patch, MagicMock

def test_argo_cd_api_yaml_import_error():
    """Test YAML import error in argo_cd_api.py by monkey-patching sys.modules"""
    # Save the original module
    original_yaml = sys.modules.get('yaml')
    
    try:
        # Remove yaml from sys.modules
        if 'yaml' in sys.modules:
            del sys.modules['yaml']
        
        # Make importing yaml raise ImportError
        def mock_import(name, *args, **kwargs):
            if name == 'yaml':
                raise ImportError("No module named 'yaml'")
            return importlib.__import__(name, *args, **kwargs)
            
        # Monkey patch the builtin __import__ function
        original_import = __import__
        try:
            sys.modules['builtins'].__import__ = mock_import
            
            # Now importing argo_cd_api should raise the expected ImportError
            with pytest.raises(ImportError) as excinfo:
                import app.argo_cd_api_test
                
            assert "PyYAML is required" in str(excinfo.value)
            
        finally:
            # Restore original import
            sys.modules['builtins'].__import__ = original_import
    
    finally:
        # Restore the original yaml module if it existed
        if original_yaml:
            sys.modules['yaml'] = original_yaml

def test_argo_cd_api_test_full_coverage():
    """Test full coverage of the argo_cd_api_test.py file by using importlib"""
    # Clear the module from sys.modules if it's already been imported
    if 'app.argo_cd_api_test' in sys.modules:
        del sys.modules['app.argo_cd_api_test']
    
    # We need to patch the actual import mechanism to force an ImportError for yaml
    def mock_import(name, *args, **kwargs):
        if name == 'yaml':
            raise ImportError("No module named 'yaml'")
        return importlib.__import__(name, *args, **kwargs)
    
    # Use the fixed import mock
    with patch('builtins.__import__', side_effect=mock_import):
        # Now try to import the module, which should fail due to missing yaml
        with pytest.raises(ImportError) as excinfo:
            import app.argo_cd_api_test
            
        # Verify the error message
        assert "PyYAML is required" in str(excinfo.value)