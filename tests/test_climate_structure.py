"""Test the structure of climate.py without importing Home Assistant."""

import sys
import os
import ast

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_climate_file_structure():
    """Test that climate.py has the correct structure by parsing the AST."""
    
    # Read the climate.py file
    with open('custom_components/smart_climate/climate.py', 'r') as f:
        content = f.read()
    
    # Parse the AST
    tree = ast.parse(content)
    
    # Find the SmartClimateEntity class
    smart_climate_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'SmartClimateEntity':
            smart_climate_class = node
            break
    
    assert smart_climate_class is not None, "SmartClimateEntity class not found"
    
    # Check that it inherits from ClimateEntity
    assert len(smart_climate_class.bases) == 1, "SmartClimateEntity should inherit from one class"
    assert smart_climate_class.bases[0].id == 'ClimateEntity', "Should inherit from ClimateEntity"
    
    # Check for required methods (both sync and async)
    methods = []
    for node in smart_climate_class.body:
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            methods.append(node.name)
    
    required_methods = [
        '__init__',
        'unique_id',
        'name',
        'current_temperature',
        'target_temperature',
        'preset_modes',
        'preset_mode',
        'hvac_mode',
        'hvac_modes',
        'supported_features',
        'async_set_temperature',
        'async_set_preset_mode',
        'async_set_hvac_mode'
    ]
    
    for method in required_methods:
        assert method in methods, f"Missing required method: {method}"
    
    print("✓ SmartClimateEntity structure test passed")
    print(f"✓ Found {len(methods)} methods in SmartClimateEntity")


def test_init_method_parameters():
    """Test that __init__ has the correct parameters."""
    
    # Read and parse the climate.py file
    with open('custom_components/smart_climate/climate.py', 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    # Find the __init__ method
    init_method = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'SmartClimateEntity':
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name == '__init__':
                    init_method = method
                    break
    
    assert init_method is not None, "__init__ method not found"
    
    # Check parameters
    params = [arg.arg for arg in init_method.args.args]
    expected_params = [
        'self', 'hass', 'config', 'wrapped_entity_id', 'room_sensor_id',
        'offset_engine', 'sensor_manager', 'mode_manager', 
        'temperature_controller', 'coordinator'
    ]
    
    for param in expected_params:
        assert param in params, f"Missing parameter: {param}"
    
    print("✓ __init__ method parameters test passed")
    print(f"✓ Found {len(params)} parameters in __init__")


def test_property_methods():
    """Test that required properties are defined."""
    
    # Read and parse the climate.py file
    with open('custom_components/smart_climate/climate.py', 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    # Find SmartClimateEntity class
    smart_climate_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'SmartClimateEntity':
            smart_climate_class = node
            break
    
    # Find methods with @property decorator
    property_methods = []
    for node in smart_climate_class.body:
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == 'property':
                    property_methods.append(node.name)
    
    required_properties = [
        'unique_id',
        'name', 
        'current_temperature',
        'target_temperature',
        'preset_modes',
        'preset_mode',
        'hvac_mode',
        'hvac_modes',
        'supported_features',
        'min_temp',
        'max_temp',
        'temperature_unit'
    ]
    
    for prop in required_properties:
        assert prop in property_methods, f"Missing property: {prop}"
    
    print("✓ Property methods test passed")
    print(f"✓ Found {len(property_methods)} property methods")


def test_instance_variables():
    """Test that __init__ sets all required instance variables."""
    
    # Read and parse the climate.py file
    with open('custom_components/smart_climate/climate.py', 'r') as f:
        content = f.read()
    
    # Check that all required instance variables are set
    required_vars = [
        '_wrapped_entity_id',
        '_room_sensor_id',
        '_outdoor_sensor_id',
        '_power_sensor_id',
        '_offset_engine',
        '_sensor_manager',
        '_mode_manager',
        '_temperature_controller',
        '_coordinator',
        '_config',
        '_last_offset',
        '_manual_override'
    ]
    
    for var in required_vars:
        assert var in content, f"Missing instance variable assignment: {var}"
    
    print("✓ Instance variables test passed")


def test_preset_modes_hardcoded():
    """Test that preset_modes returns the correct hardcoded values."""
    
    # Read and parse the climate.py file
    with open('custom_components/smart_climate/climate.py', 'r') as f:
        content = f.read()
    
    # Check that preset_modes returns the expected list
    assert '["none", "away", "sleep", "boost"]' in content, "preset_modes should return correct list"
    
    print("✓ Preset modes hardcoded values test passed")


def test_async_methods():
    """Test that async methods are properly defined."""
    
    # Read and parse the climate.py file
    with open('custom_components/smart_climate/climate.py', 'r') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    # Find SmartClimateEntity class
    smart_climate_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'SmartClimateEntity':
            smart_climate_class = node
            break
    
    # Find async methods
    async_methods = []
    for node in smart_climate_class.body:
        if isinstance(node, ast.AsyncFunctionDef):
            async_methods.append(node.name)
    
    required_async_methods = [
        'async_set_temperature',
        'async_set_preset_mode',
        'async_set_hvac_mode',
        'async_added_to_hass',
        'async_will_remove_from_hass'
    ]
    
    for method in required_async_methods:
        assert method in async_methods, f"Missing async method: {method}"
    
    print("✓ Async methods test passed")
    print(f"✓ Found {len(async_methods)} async methods")


if __name__ == "__main__":
    test_climate_file_structure()
    test_init_method_parameters()
    test_property_methods()
    test_instance_variables()
    test_preset_modes_hardcoded()
    test_async_methods()
    print("\n✅ All structure tests passed!")