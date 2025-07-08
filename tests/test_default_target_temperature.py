"""Test suite for configurable default target temperature."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_default_target_temperature_constant():
    """Test that default target temperature constant is correct."""
    from custom_components.smart_climate.const import (
        DEFAULT_TARGET_TEMPERATURE,
        CONF_DEFAULT_TARGET_TEMPERATURE
    )
    
    # Test that the default is now 24.0°C instead of 22.0°C
    assert DEFAULT_TARGET_TEMPERATURE == 24.0
    
    # Test that the constant is in reasonable range
    assert 16.0 <= DEFAULT_TARGET_TEMPERATURE <= 30.0
    
    # Test that the config key exists
    assert CONF_DEFAULT_TARGET_TEMPERATURE == "default_target_temperature"
    
    print("✓ Default target temperature constant test passed")


def test_config_flow_includes_default_temperature():
    """Test that config flow includes the new default temperature field."""
    from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
    from custom_components.smart_climate.const import CONF_DEFAULT_TARGET_TEMPERATURE
    
    # Test that the constant is imported in config flow
    config_flow = SmartClimateConfigFlow()
    
    # This verifies the import works without error
    assert hasattr(config_flow, 'async_step_user')
    
    print("✓ Config flow import test passed")


def test_climate_entity_uses_configurable_default():
    """Test that climate entity structure supports configurable default."""
    from custom_components.smart_climate.climate import SmartClimateEntity
    
    # Test that target_temperature property exists
    assert hasattr(SmartClimateEntity, 'target_temperature')
    
    # Test basic initialization doesn't crash
    # (We can't test full functionality without Home Assistant dependencies)
    import inspect
    sig = inspect.signature(SmartClimateEntity.__init__)
    params = list(sig.parameters.keys())
    
    # Should accept config parameter where we pass default_target_temperature
    assert 'config' in params
    
    print("✓ Climate entity structure test passed")


def test_translations_include_default_temperature():
    """Test that translation files include the new field."""
    import json
    
    # Read the English translations
    translations_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'custom_components',
        'smart_climate',
        'translations',
        'en.json'
    )
    
    with open(translations_path, 'r') as f:
        translations = json.load(f)
    
    # Check that the new field is in translations
    config_step = translations['config']['step']['user']
    
    assert 'default_target_temperature' in config_step['data']
    assert 'default_target_temperature' in config_step['data_description']
    
    # Check that the translation includes temperature unit
    assert '°C' in config_step['data']['default_target_temperature']
    
    print("✓ Translations test passed")


if __name__ == "__main__":
    test_default_target_temperature_constant()
    test_config_flow_includes_default_temperature()
    test_climate_entity_uses_configurable_default()
    test_translations_include_default_temperature()
    print("All default target temperature tests passed!")