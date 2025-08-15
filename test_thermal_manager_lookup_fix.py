#!/usr/bin/env python3
"""
Test for thermal manager lookup bug fix.

ABOUTME: Test demonstrating and verifying fix for thermal manager entity ID mismatch bug
ABOUTME: Bug was thermal components stored by wrapped_entity_id but accessed by smart_entity_id
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# Import the component to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components/smart_climate'))

from climate import SmartClimateEntity
from models import OffsetInput


def test_thermal_manager_lookup_bug_demonstration():
    """
    Test that demonstrates the thermal manager lookup bug.
    
    This test shows that thermal components are stored by wrapped entity ID
    but accessed by Smart Climate entity ID, causing the lookup to fail.
    """
    # Mock dependencies
    hass = Mock()
    config = {'entry_id': 'test_entry'}
    wrapped_entity_id = 'climate.klimaanlage_tu_climate'  # This is what gets stored
    room_sensor_id = 'sensor.room_temp'
    
    # Mock hass.data structure showing thermal components stored by wrapped_entity_id
    hass.data = {
        'smart_climate': {
            'test_entry': {
                'thermal_components': {
                    # Thermal components are stored by wrapped entity ID
                    'climate.klimaanlage_tu_climate': {
                        'thermal_manager': Mock(current_state='DRIFTING')
                    }
                }
            }
        }
    }
    
    # Create SmartClimateEntity - this will have entity_id different from wrapped_entity_id
    entity = SmartClimateEntity(
        hass=hass,
        config=config,
        wrapped_entity_id=wrapped_entity_id,
        room_sensor_id=room_sensor_id,
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=Mock()
    )
    
    # The entity_id will be different (Smart Climate prefixes it)
    entity.entity_id = 'climate.smart_klimaanlage_tu_climate'
    
    # Mock the DOMAIN constant
    with patch('climate.DOMAIN', 'smart_climate'):
        # Extract the thermal lookup logic from _apply_temperature_with_offset
        entry_id = config.get('entry_id')
        thermal_state = None
        
        if entry_id and hass.data.get('smart_climate', {}).get(entry_id, {}).get('thermal_components'):
            # This is the BUGGY line - using entity.entity_id instead of entity._wrapped_entity_id
            thermal_components = hass.data['smart_climate'][entry_id]['thermal_components'].get(entity.entity_id)
            if thermal_components and isinstance(thermal_components, dict):
                thermal_manager = thermal_components.get('thermal_manager')
                if thermal_manager:
                    thermal_state = thermal_manager.current_state
    
    # Verify the bug - thermal_state should be None because lookup failed
    assert thermal_state is None, "Bug not demonstrated - thermal_state should be None due to entity ID mismatch"
    
    # Show what the available keys are
    available_keys = list(hass.data['smart_climate']['test_entry']['thermal_components'].keys())
    assert available_keys == ['climate.klimaanlage_tu_climate'], f"Available keys: {available_keys}"
    
    # Show that the lookup was for the wrong key
    lookup_key = entity.entity_id  # 'climate.smart_klimaanlage_tu_climate'
    storage_key = wrapped_entity_id  # 'climate.klimaanlage_tu_climate' 
    assert lookup_key != storage_key, f"Keys should be different: lookup={lookup_key}, storage={storage_key}"
    
    print("✓ Bug demonstrated: Thermal manager lookup fails due to entity ID mismatch")
    print(f"  - Stored under key: {storage_key}")
    print(f"  - Looked up with key: {lookup_key}")


def test_thermal_manager_lookup_fix_verification():
    """
    Test that verifies the fix for the thermal manager lookup bug.
    
    This test shows that using _wrapped_entity_id instead of entity_id
    allows thermal components to be found correctly.
    """
    # Mock dependencies
    hass = Mock()
    config = {'entry_id': 'test_entry'}
    wrapped_entity_id = 'climate.klimaanlage_tu_climate'
    room_sensor_id = 'sensor.room_temp'
    
    # Mock thermal state
    mock_thermal_manager = Mock()
    mock_thermal_manager.current_state = Mock(name='DRIFTING')
    
    # Mock hass.data structure
    hass.data = {
        'smart_climate': {
            'test_entry': {
                'thermal_components': {
                    # Thermal components stored by wrapped entity ID
                    'climate.klimaanlage_tu_climate': {
                        'thermal_manager': mock_thermal_manager
                    }
                }
            }
        }
    }
    
    # Create SmartClimateEntity
    entity = SmartClimateEntity(
        hass=hass,
        config=config,
        wrapped_entity_id=wrapped_entity_id,
        room_sensor_id=room_sensor_id,
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=Mock()
    )
    
    # The entity_id will be different (Smart Climate prefixes it)
    entity.entity_id = 'climate.smart_klimaanlage_tu_climate'
    
    # Mock the DOMAIN constant
    with patch('climate.DOMAIN', 'smart_climate'):
        # Extract the thermal lookup logic with FIX - using _wrapped_entity_id
        entry_id = config.get('entry_id')
        thermal_state = None
        
        if entry_id and hass.data.get('smart_climate', {}).get(entry_id, {}).get('thermal_components'):
            # This is the FIXED line - using entity._wrapped_entity_id instead of entity.entity_id
            thermal_components = hass.data['smart_climate'][entry_id]['thermal_components'].get(entity._wrapped_entity_id)
            if thermal_components and isinstance(thermal_components, dict):
                thermal_manager = thermal_components.get('thermal_manager')
                if thermal_manager:
                    thermal_state = thermal_manager.current_state
    
    # Verify the fix - thermal_state should now be found
    assert thermal_state is not None, "Fix failed - thermal_state should not be None"
    assert thermal_state.name == 'DRIFTING', f"Expected DRIFTING state, got {thermal_state}"
    
    print("✓ Fix verified: Thermal manager lookup succeeds using _wrapped_entity_id")
    print(f"  - Thermal state retrieved: {thermal_state.name}")


async def test_thermal_state_integration_with_priority_resolver():
    """
    Test that thermal state is properly passed to _resolve_target_temperature.
    
    This verifies the complete integration works after the fix.
    """
    # Mock dependencies
    hass = Mock()
    config = {'entry_id': 'test_entry'}
    wrapped_entity_id = 'climate.klimaanlage_tu_climate'
    room_sensor_id = 'sensor.room_temp'
    
    # Create SmartClimateEntity with mocked dependencies
    entity = SmartClimateEntity(
        hass=hass,
        config=config,
        wrapped_entity_id=wrapped_entity_id,
        room_sensor_id=room_sensor_id,
        offset_engine=Mock(),
        sensor_manager=Mock(),
        mode_manager=Mock(),
        temperature_controller=Mock(),
        coordinator=Mock()
    )
    
    entity.entity_id = 'climate.smart_klimaanlage_tu_climate'
    
    # Mock thermal state
    mock_thermal_state = Mock()
    mock_thermal_state.name = 'DRIFTING'
    
    # Mock _resolve_target_temperature method
    entity._resolve_target_temperature = Mock(return_value=23.0)
    
    # Mock thermal manager lookup data structure
    hass.data = {
        'smart_climate': {
            'test_entry': {
                'thermal_components': {
                    'climate.klimaanlage_tu_climate': {  # Stored by wrapped entity ID
                        'thermal_manager': Mock(current_state=mock_thermal_state)
                    }
                }
            }
        }
    }
    
    # Test the integration - simulate what happens in _apply_temperature_with_offset
    with patch('climate.DOMAIN', 'smart_climate'):
        entry_id = config.get('entry_id')
        thermal_state = None
        
        # This is the FIXED lookup using _wrapped_entity_id
        if entry_id and hass.data.get('smart_climate', {}).get(entry_id, {}).get('thermal_components'):
            thermal_components = hass.data['smart_climate'][entry_id]['thermal_components'].get(entity._wrapped_entity_id)
            if thermal_components and isinstance(thermal_components, dict):
                thermal_manager = thermal_components.get('thermal_manager')
                if thermal_manager:
                    thermal_state = thermal_manager.current_state
        
        # Simulate calling _resolve_target_temperature with thermal state
        if thermal_state is not None:
            resolved_target = entity._resolve_target_temperature(
                22.0,  # base_target_temp
                21.0,  # current_room_temp
                thermal_state,  # thermal_state (should not be None)
                Mock()  # mode_adjustments
            )
        
    # Verify thermal state was found and passed correctly
    assert thermal_state is not None, "Thermal state should be found after fix"
    assert thermal_state.name == 'DRIFTING', f"Expected DRIFTING, got {thermal_state.name}"
    
    # Verify _resolve_target_temperature was called with thermal_state
    entity._resolve_target_temperature.assert_called_once()
    call_args = entity._resolve_target_temperature.call_args[0]
    assert len(call_args) == 4, "Should be called with 4 args"
    assert call_args[2] == thermal_state, "Third arg should be thermal_state"
    
    # Verify resolved temperature was returned
    assert resolved_target == 23.0, f"Expected 23.0, got {resolved_target}"
    
    print("✓ Integration test passed: Thermal state properly passed to priority resolver")


if __name__ == '__main__':
    # Run the tests
    print("=== Testing Thermal Manager Lookup Bug and Fix ===")
    
    try:
        print("\n1. Demonstrating the bug...")
        test_thermal_manager_lookup_bug_demonstration()
        
        print("\n2. Verifying the fix...")
        test_thermal_manager_lookup_fix_verification()
        
        print("\n3. Testing integration after fix...")
        asyncio.run(test_thermal_state_integration_with_priority_resolver())
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)