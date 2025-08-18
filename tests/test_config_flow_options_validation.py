"""Test config flow options validation for optional entities."""
import sys
import os
from unittest.mock import AsyncMock, Mock, patch

# Add project root to path  
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
    from custom_components.smart_climate.const import (
        CONF_PRESENCE_ENTITY_ID,
        CONF_WEATHER_ENTITY_ID, 
        CONF_CALENDAR_ENTITY_ID,
        CONF_MANUAL_OVERRIDE_ENTITY_ID,
        CONF_LEARNING_PROFILE,
    )
    IMPORT_SUCCESS = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORT_SUCCESS = False


def mock_config_entry():
    """Create a mock config entry for testing."""
    entry = Mock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "climate_entity": "climate.test",
        "room_sensor": "sensor.room_temp",
    }
    entry.options = {
        "probe_scheduler_enabled": True,
        "learning_profile": "comfort",
        "weather_entity_id": "weather.home",
    }
    return entry


def create_options_flow():
    """Create an options flow instance."""
    flow = SmartClimateOptionsFlow()
    flow.hass = Mock()
    flow.config_entry = mock_config_entry()
    return flow


def test_clean_entity_ids_method():
    """Test the _clean_entity_ids method directly."""
    print("Testing _clean_entity_ids method...")
    options_flow = create_options_flow()
    
    try:
        # Test data with empty strings for optional entities
        user_input = {
            "presence_entity_id": "",
            "calendar_entity_id": "",
            "manual_override_entity_id": "",
            "weather_entity_id": "weather.home",  # Should remain unchanged
            "learning_profile": "comfort",  # Should remain unchanged
        }
        
        print("Input data:", user_input)
        cleaned = options_flow._clean_entity_ids(user_input)
        print("Cleaned data:", cleaned)
        
        # Verify empty strings were cleaned to None
        success = True
        if cleaned.get("presence_entity_id") is not None:
            print("✗ presence_entity_id not cleaned properly")
            success = False
        else:
            print("✓ presence_entity_id cleaned to None")
            
        if cleaned.get("calendar_entity_id") is not None:
            print("✗ calendar_entity_id not cleaned properly") 
            success = False
        else:
            print("✓ calendar_entity_id cleaned to None")
            
        if cleaned.get("manual_override_entity_id") is not None:
            print("✗ manual_override_entity_id not cleaned properly")
            success = False
        else:
            print("✓ manual_override_entity_id cleaned to None")
            
        # Verify non-empty values remain unchanged
        if cleaned.get("weather_entity_id") != "weather.home":
            print("✗ weather_entity_id was incorrectly modified")
            success = False
        else:
            print("✓ weather_entity_id remained unchanged")
            
        if cleaned.get("learning_profile") != "comfort":
            print("✗ learning_profile was incorrectly modified")
            success = False
        else:
            print("✓ learning_profile remained unchanged")
        
        return success
        
    except Exception as e:
        print(f"✗ _clean_entity_ids method test failed: {e}")
        return False


def test_schema_defaults():
    """Test that schema uses empty string defaults for optional entities."""
    print("\nTesting schema defaults...")
    options_flow = create_options_flow()
    
    try:
        schema = options_flow._get_options_schema()
        print("✓ Schema generated successfully")
        
        # Check schema structure for our optional fields
        schema_dict = schema.schema
        success = True
        
        for field_key, field_validator in schema_dict.items():
            if hasattr(field_key, 'key'):
                field_name = field_key.key
                if field_name in [CONF_CALENDAR_ENTITY_ID, CONF_MANUAL_OVERRIDE_ENTITY_ID, CONF_PRESENCE_ENTITY_ID]:
                    default_value = field_key.default
                    if callable(default_value):
                        default_value = default_value()
                    print(f"  {field_name}: default = '{default_value}' (type: {type(default_value).__name__})")
                    
                    # For the fix, we expect empty string defaults, not None
                    if field_name in [CONF_CALENDAR_ENTITY_ID, CONF_MANUAL_OVERRIDE_ENTITY_ID, CONF_PRESENCE_ENTITY_ID]:
                        if default_value == "":
                            print(f"✓ {field_name} has correct empty string default")
                        else:
                            print(f"✗ {field_name} has incorrect default: {default_value}")
                            success = False
        
        return success
        
    except Exception as e:
        print(f"✗ Schema defaults test failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during validation: {e}")
        return False


def test_integration_simulation():
    """Test simulating the full integration with async_step_init."""
    print("\nTesting integration simulation...")
    options_flow = create_options_flow()
    
    try:
        # Mock the humidity sensors method
        options_flow._get_humidity_sensors = AsyncMock(return_value={})
        
        # Test data that would previously cause validation errors
        user_input = {
            "probe_scheduler_enabled": True,
            "learning_profile": "comfort",
            "presence_entity_id": "",  # Empty string - should be cleaned to None
            "weather_entity_id": "weather.home",
            "calendar_entity_id": "",  # Empty string - should be cleaned to None  
            "manual_override_entity_id": "",  # Empty string - should be cleaned to None
        }
        
        print("Input data:", user_input)
        
        # Test the cleaning method directly (since we can't run the full async method easily)
        cleaned_input = options_flow._clean_entity_ids(user_input)
        print("Cleaned data:", cleaned_input)
        
        # Verify the cleaning worked correctly
        success = True
        expected_output = {
            "probe_scheduler_enabled": True,
            "learning_profile": "comfort", 
            "presence_entity_id": None,  # Should be cleaned from ""
            "weather_entity_id": "weather.home",  # Should remain unchanged
            "calendar_entity_id": None,  # Should be cleaned from ""
            "manual_override_entity_id": None,  # Should be cleaned from ""
        }
        
        for key, expected_value in expected_output.items():
            actual_value = cleaned_input.get(key)
            if actual_value == expected_value:
                print(f"✓ {key}: {actual_value} (correct)")
            else:
                print(f"✗ {key}: expected {expected_value}, got {actual_value}")
                success = False
        
        return success
        
    except Exception as e:
        print(f"✗ Integration simulation failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during validation: {e}")
        return False


def run_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("TESTING OPTIONAL ENTITY VALIDATION FIX")
    print("=" * 60)
    
    if not IMPORT_SUCCESS:
        print("✗ Cannot run tests - import failed")
        return False
    
    tests = [
        test_clean_entity_ids_method,
        test_schema_defaults,
        test_integration_simulation,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test_func.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed - this confirms the bug exists")
    
    return passed == total


if __name__ == "__main__":
    run_tests()
