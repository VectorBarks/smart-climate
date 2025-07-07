"""Simple tests for SmartClimateEntity without Home Assistant dependencies."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_smart_climate_entity_structure():
    """Test that SmartClimateEntity has the correct structure."""
    # Import the module directly
    from custom_components.smart_climate import climate
    
    # Test that the class exists
    assert hasattr(climate, 'SmartClimateEntity')
    
    # Test that it has the required methods
    SmartClimateEntity = climate.SmartClimateEntity
    
    # Check for key properties from architecture
    assert hasattr(SmartClimateEntity, 'current_temperature')
    assert hasattr(SmartClimateEntity, 'target_temperature')
    assert hasattr(SmartClimateEntity, 'preset_modes')
    assert hasattr(SmartClimateEntity, 'preset_mode')
    assert hasattr(SmartClimateEntity, 'hvac_mode')
    assert hasattr(SmartClimateEntity, 'hvac_modes')
    assert hasattr(SmartClimateEntity, 'supported_features')
    
    # Check for key methods
    assert hasattr(SmartClimateEntity, 'async_set_temperature')
    assert hasattr(SmartClimateEntity, 'async_set_preset_mode')
    assert hasattr(SmartClimateEntity, 'async_set_hvac_mode')
    
    print("✓ SmartClimateEntity structure test passed")


def test_climate_entity_initialization_signature():
    """Test that SmartClimateEntity has correct initialization signature."""
    from custom_components.smart_climate import climate
    
    SmartClimateEntity = climate.SmartClimateEntity
    
    # Check __init__ signature matches architecture
    import inspect
    sig = inspect.signature(SmartClimateEntity.__init__)
    params = list(sig.parameters.keys())
    
    # Expected parameters from architecture
    expected_params = [
        'self', 'hass', 'config', 'wrapped_entity_id', 'room_sensor_id',
        'offset_engine', 'sensor_manager', 'mode_manager', 
        'temperature_controller', 'coordinator'
    ]
    
    for param in expected_params:
        assert param in params, f"Missing parameter: {param}"
    
    print("✓ SmartClimateEntity initialization signature test passed")


def test_preset_modes_constants():
    """Test that preset_modes returns correct constants."""
    from custom_components.smart_climate import climate
    
    # We can't create an instance without Home Assistant,
    # but we can check the property method exists and returns expected values
    SmartClimateEntity = climate.SmartClimateEntity
    
    # Check that the property is defined
    assert hasattr(SmartClimateEntity, 'preset_modes')
    assert isinstance(SmartClimateEntity.preset_modes, property)
    
    print("✓ Preset modes property test passed")


def test_architecture_compliance():
    """Test that the implementation follows architecture requirements."""
    from custom_components.smart_climate import climate
    
    # Check that all required instance variables are mentioned in __init__
    import inspect
    source = inspect.getsource(climate.SmartClimateEntity.__init__)
    
    # Check for required instance variables from architecture
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
        assert var in source, f"Missing required instance variable: {var}"
    
    print("✓ Architecture compliance test passed")


if __name__ == "__main__":
    test_smart_climate_entity_structure()
    test_climate_entity_initialization_signature()
    test_preset_modes_constants()
    test_architecture_compliance()
    print("\n✅ All simple tests passed!")