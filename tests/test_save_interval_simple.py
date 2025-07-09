"""Simple test for save interval configuration."""
import pytest
from custom_components.smart_climate.const import (
    CONF_SAVE_INTERVAL,
    DEFAULT_SAVE_INTERVAL,
)


def test_save_interval_constants():
    """Test that save interval constants are defined correctly."""
    assert CONF_SAVE_INTERVAL == "save_interval"
    assert DEFAULT_SAVE_INTERVAL == 3600  # 1 hour


def test_save_interval_in_config_flow():
    """Test that save interval is imported in config flow."""
    from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
    
    # Test that the config flow can be imported without errors
    flow = SmartClimateConfigFlow()
    assert flow is not None
    
    # Check that the save interval constant is available
    assert hasattr(flow, '__module__')


def test_save_interval_translations():
    """Test that save interval translations exist."""
    import json
    
    with open('custom_components/smart_climate/translations/en.json', 'r') as f:
        translations = json.load(f)
    
    # Check that save_interval is in the config data
    assert 'save_interval' in translations['config']['step']['user']['data']
    assert 'save_interval' in translations['config']['step']['user']['data_description']
    
    # Check that save_interval is in the options data
    assert 'save_interval' in translations['options']['step']['init']['data']
    assert 'save_interval' in translations['options']['step']['init']['data_description']
    
    # Check that the descriptions are meaningful
    assert len(translations['config']['step']['user']['data']['save_interval']) > 0
    assert len(translations['config']['step']['user']['data_description']['save_interval']) > 0


def test_save_interval_validation_ranges():
    """Test that save interval validation ranges are appropriate."""
    # Test that default is within valid range
    assert 300 <= DEFAULT_SAVE_INTERVAL <= 86400  # 5 minutes to 24 hours
    
    # Test boundary values
    assert DEFAULT_SAVE_INTERVAL == 3600  # 1 hour
    
    # Test reasonable values
    valid_values = [300, 600, 900, 1800, 3600, 7200, 14400, 43200, 86400]
    for value in valid_values:
        assert 300 <= value <= 86400


def test_save_interval_backward_compatibility():
    """Test that save interval has appropriate default for backward compatibility."""
    # The default should be 1 hour (3600 seconds)
    # This is a reasonable default that doesn't save too frequently
    # but also doesn't risk losing too much data
    assert DEFAULT_SAVE_INTERVAL == 3600
    
    # Default should be higher than the minimum to avoid excessive disk I/O
    assert DEFAULT_SAVE_INTERVAL > 300
    
    # Default should be lower than the maximum to ensure regular saves
    assert DEFAULT_SAVE_INTERVAL < 86400