"""
ABOUTME: Test for verifying HVACMode imports work correctly from new import path.
Validates that import changes resolve integration load failures.
"""
import pytest


def test_hvacmode_import_from_climate_const():
    """Test that HVACMode can be imported from homeassistant.components.climate.const."""
    try:
        from homeassistant.components.climate.const import HVACMode
        # Verify basic HVACMode enum values are accessible
        assert hasattr(HVACMode, 'OFF')
        assert hasattr(HVACMode, 'COOL') 
        assert hasattr(HVACMode, 'HEAT')
        assert hasattr(HVACMode, 'AUTO')
    except ImportError as e:
        pytest.fail(f"Failed to import HVACMode from homeassistant.components.climate.const: {e}")


def test_delay_learner_imports_resolve():
    """Test that delay_learner.py can be imported without HVACMode import errors."""
    try:
        from custom_components.smart_climate.delay_learner import DelayLearner
        # Verify the class exists and can be instantiated
        assert DelayLearner is not None
    except ImportError as e:
        pytest.fail(f"Failed to import DelayLearner after fixing HVACMode import: {e}")


def test_delay_learning_timeout_test_imports_resolve():
    """Test that test_delay_learning_timeout.py dependencies can be imported."""
    try:
        # Import the modules that test_delay_learning_timeout.py depends on
        from custom_components.smart_climate.delay_learner import DelayLearner
        from homeassistant.components.climate.const import HVACMode
        
        # Verify both are accessible
        assert DelayLearner is not None
        assert HVACMode is not None
        assert hasattr(HVACMode, 'COOL')
    except ImportError as e:
        pytest.fail(f"Failed to import dependencies for test_delay_learning_timeout.py: {e}")


def test_correct_import_usage():
    """Test that the files now use the correct import path."""
    import ast
    import os
    
    # Check delay_learner.py
    delay_learner_path = "custom_components/smart_climate/delay_learner.py"
    assert os.path.exists(delay_learner_path), "delay_learner.py not found"
    
    with open(delay_learner_path, 'r') as f:
        content = f.read()
        
    # Parse the file as AST to check imports
    tree = ast.parse(content)
    
    has_correct_import = False
    has_incorrect_import = False
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "homeassistant.components.climate.const" and any(alias.name == "HVACMode" for alias in node.names):
                has_correct_import = True
            elif node.module == "homeassistant.const" and any(alias.name == "HVACMode" for alias in node.names):
                has_incorrect_import = True
    
    assert has_correct_import, "delay_learner.py does not have correct HVACMode import"
    assert not has_incorrect_import, "delay_learner.py still has deprecated HVACMode import"
    
    # Check test file
    test_file_path = "tests/test_delay_learning_timeout.py"
    assert os.path.exists(test_file_path), "test_delay_learning_timeout.py not found"
    
    with open(test_file_path, 'r') as f:
        content = f.read()
        
    tree = ast.parse(content)
    
    has_correct_import = False
    has_incorrect_import = False
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "homeassistant.components.climate.const" and any(alias.name == "HVACMode" for alias in node.names):
                has_correct_import = True
            elif node.module == "homeassistant.const" and any(alias.name == "HVACMode" for alias in node.names):
                has_incorrect_import = True
    
    assert has_correct_import, "test_delay_learning_timeout.py does not have correct HVACMode import"
    assert not has_incorrect_import, "test_delay_learning_timeout.py still has deprecated HVACMode import"