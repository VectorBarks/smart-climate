"""Integration test for startup timeout configuration."""

def test_startup_timeout_in_config_flow_file():
    """Test that startup timeout configuration is present in config_flow.py file."""
    import os
    
    # Read the config flow file
    config_flow_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "custom_components", 
        "smart_climate", 
        "config_flow.py"
    )
    
    with open(config_flow_path, 'r') as f:
        content = f.read()
    
    # Verify imports
    assert "CONF_STARTUP_TIMEOUT," in content, "CONF_STARTUP_TIMEOUT not imported"
    assert "STARTUP_TIMEOUT_SEC," in content, "STARTUP_TIMEOUT_SEC not imported"
    
    # Verify field is in options schema
    assert "vol.Optional(\n                CONF_STARTUP_TIMEOUT," in content, "CONF_STARTUP_TIMEOUT field not found"
    
    # Verify default value pattern
    assert "current_options.get(CONF_STARTUP_TIMEOUT, current_config.get(CONF_STARTUP_TIMEOUT, STARTUP_TIMEOUT_SEC))" in content, "Default value pattern not found"
    
    # Verify NumberSelector configuration
    assert "selector.NumberSelector(" in content, "NumberSelector not used"
    assert "min=30," in content, "Minimum value 30 not found"
    assert "max=300," in content, "Maximum value 300 not found"
    assert "step=10," in content, "Step value 10 not found"
    assert 'unit_of_measurement="seconds"' in content, "Unit of measurement not found"
    assert "mode=selector.NumberSelectorMode.BOX" in content, "BOX mode not found"

def test_startup_timeout_constants_available():
    """Test that startup timeout constants are properly defined and accessible."""
    from custom_components.smart_climate.const import CONF_STARTUP_TIMEOUT, STARTUP_TIMEOUT_SEC
    
    # Test constant values
    assert CONF_STARTUP_TIMEOUT == "startup_timeout"
    assert STARTUP_TIMEOUT_SEC == 90
    assert isinstance(STARTUP_TIMEOUT_SEC, int)
    assert 30 <= STARTUP_TIMEOUT_SEC <= 300

def test_config_flow_imports_correctly():
    """Test that config flow can import startup timeout constants without error."""
    try:
        # This import should succeed without any errors
        from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
        from custom_components.smart_climate.const import CONF_STARTUP_TIMEOUT, STARTUP_TIMEOUT_SEC
        
        # Basic verification that imports worked
        assert SmartClimateOptionsFlow is not None
        assert CONF_STARTUP_TIMEOUT == "startup_timeout"  
        assert STARTUP_TIMEOUT_SEC == 90
        
        import_success = True
    except Exception as e:
        import_success = False
        print(f"Import failed: {e}")
    
    assert import_success, "Config flow imports failed"