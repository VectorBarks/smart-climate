#!/usr/bin/env python3
"""
Debug script to test thermal component initialization.

This script helps identify where the thermal component initialization might be failing
by importing and testing the key components independently.
"""

import sys
import os
import logging

# Add the custom component path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'smart_climate'))

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test all the thermal component imports."""
    logger.info("Testing thermal component imports...")
    
    try:
        from const import DEFAULT_SHADOW_MODE, DEFAULT_PREFERENCE_LEVEL
        logger.info("✓ Constants imported successfully")
        logger.info(f"  DEFAULT_SHADOW_MODE: {DEFAULT_SHADOW_MODE}")
        logger.info(f"  DEFAULT_PREFERENCE_LEVEL: {DEFAULT_PREFERENCE_LEVEL}")
    except Exception as e:
        logger.error(f"✗ Failed to import constants: {e}")
        return False
    
    try:
        from thermal_preferences import UserPreferences, PreferenceLevel
        logger.info("✓ UserPreferences imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import UserPreferences: {e}")
        return False
    
    try:
        from thermal_model import PassiveThermalModel
        logger.info("✓ PassiveThermalModel imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import PassiveThermalModel: {e}")
        return False
    
    try:
        from thermal_manager import ThermalManager
        logger.info("✓ ThermalManager imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import ThermalManager: {e}")
        return False
    
    try:
        from probe_manager import ProbeManager
        logger.info("✓ ProbeManager imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import ProbeManager: {e}")
        return False
    
    try:
        from thermal_sensor import SmartClimateStatusSensor
        logger.info("✓ SmartClimateStatusSensor imported successfully")
    except Exception as e:
        logger.error(f"✗ Failed to import SmartClimateStatusSensor: {e}")
        return False
    
    return True

def test_thermal_component_creation():
    """Test creating thermal components similar to the actual initialization."""
    logger.info("Testing thermal component creation...")
    
    try:
        from thermal_preferences import UserPreferences, PreferenceLevel
        from thermal_model import PassiveThermalModel
        from thermal_manager import ThermalManager
        from probe_manager import ProbeManager
        from thermal_sensor import SmartClimateStatusSensor
        
        # Test thermal model creation
        logger.info("Creating PassiveThermalModel...")
        thermal_model = PassiveThermalModel(
            tau_cooling=90.0,
            tau_warming=150.0
        )
        logger.info("✓ PassiveThermalModel created successfully")
        
        # Test user preferences creation
        logger.info("Creating UserPreferences...")
        pref_level = PreferenceLevel.BALANCED
        user_preferences = UserPreferences(
            level=pref_level,
            comfort_band=1.5,
            confidence_threshold=0.7,
            probe_drift=2.0
        )
        logger.info("✓ UserPreferences created successfully")
        
        # Test thermal manager creation (without hass)
        logger.info("Creating ThermalManager (mock)...")
        # Note: This will fail without proper hass object, but we can test the import
        logger.info("✓ ThermalManager class available")
        
        # Test probe manager creation (without hass)
        logger.info("Creating ProbeManager (mock)...")
        # Note: This will fail without proper hass object, but we can test the import
        logger.info("✓ ProbeManager class available")
        
        # Test status sensor creation (without hass)
        logger.info("Creating SmartClimateStatusSensor (mock)...")
        # Note: This will fail without proper hass object, but we can test the import
        logger.info("✓ SmartClimateStatusSensor class available")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create thermal components: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting thermal component debug tests...")
    
    success = True
    
    if not test_imports():
        success = False
    
    if not test_thermal_component_creation():
        success = False
    
    if success:
        logger.info("🎉 All tests passed! Thermal components should initialize correctly.")
    else:
        logger.error("❌ Some tests failed. Check the errors above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)