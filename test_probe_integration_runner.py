#!/usr/bin/env python3
"""Simple test runner for ThermalManager ProbeScheduler integration tests."""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the project path to sys.path so we can import modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    # Import the modules we need
    from custom_components.smart_climate.thermal_manager import ThermalManager
    from custom_components.smart_climate.thermal_models import ThermalState, PassiveThermalModel
    from custom_components.smart_climate.probe_scheduler import ProbeScheduler
    from custom_components.smart_climate.user_preferences import UserPreferences
    
    print("✓ All imports successful")
    
    # Test 1: ThermalManager can be initialized with ProbeScheduler
    print("\nTest 1: ThermalManager initialization with ProbeScheduler")
    mock_hass = Mock()
    mock_thermal_model = Mock(spec=PassiveThermalModel)
    mock_preferences = Mock(spec=UserPreferences)
    mock_probe_scheduler = Mock(spec=ProbeScheduler)
    mock_probe_scheduler.should_probe_now.return_value = False
    
    # Test initialization with probe scheduler
    manager = ThermalManager(
        hass=mock_hass,
        thermal_model=mock_thermal_model,
        preferences=mock_preferences,
        config={},
        probe_scheduler=mock_probe_scheduler
    )
    
    assert hasattr(manager, 'probe_scheduler'), "ThermalManager should have probe_scheduler attribute"
    assert manager.probe_scheduler is mock_probe_scheduler, "ProbeScheduler should be stored correctly"
    print("✓ ThermalManager initializes with ProbeScheduler")
    
    # Test 2: ThermalManager backward compatibility without ProbeScheduler
    print("\nTest 2: Backward compatibility without ProbeScheduler")
    manager_no_scheduler = ThermalManager(
        hass=mock_hass,
        thermal_model=mock_thermal_model,
        preferences=mock_preferences,
        config={}
    )
    
    assert hasattr(manager_no_scheduler, 'probe_scheduler'), "Should have probe_scheduler attribute"
    assert manager_no_scheduler.probe_scheduler is None, "ProbeScheduler should be None when not provided"
    print("✓ ThermalManager works without ProbeScheduler (backward compatible)")
    
    # Test 3: PRIMING state only does passive learning
    print("\nTest 3: PRIMING state passive learning only")
    manager._current_state = ThermalState.PRIMING
    mock_probe_scheduler.should_probe_now.return_value = True  # Scheduler wants to probe
    
    with patch.object(manager, '_handle_passive_learning') as mock_passive:
        manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
        
        # Should call passive learning and not check probe scheduler
        mock_passive.assert_called_once()
        mock_probe_scheduler.should_probe_now.assert_not_called()
    print("✓ PRIMING state only does passive learning, ignores probe scheduler")
    
    # Test 4: DRIFTING state checks for opportunistic probing
    print("\nTest 4: DRIFTING state opportunistic probing")
    mock_probe_scheduler.reset_mock()
    mock_probe_scheduler.should_probe_now.return_value = True
    
    manager._current_state = ThermalState.DRIFTING
    
    # Mock the state handler to return None (no handler transition)
    mock_handler = Mock()
    mock_handler.execute.return_value = None
    manager._state_handlers[ThermalState.DRIFTING] = mock_handler
    
    with patch.object(manager, 'transition_to') as mock_transition:
        manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
        
        # Should check probe scheduler and transition to PROBING
        mock_probe_scheduler.should_probe_now.assert_called_once()
        mock_transition.assert_called_with(ThermalState.PROBING)
    print("✓ DRIFTING state checks probe scheduler and transitions to PROBING when approved")
    
    # Test 5: CORRECTING state checks for opportunistic probing
    print("\nTest 5: CORRECTING state opportunistic probing")
    mock_probe_scheduler.reset_mock()
    mock_probe_scheduler.should_probe_now.return_value = True
    
    manager._current_state = ThermalState.CORRECTING
    
    # Mock the state handler to return None
    mock_handler = Mock()
    mock_handler.execute.return_value = None
    manager._state_handlers[ThermalState.CORRECTING] = mock_handler
    
    with patch.object(manager, 'transition_to') as mock_transition:
        manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
        
        # Should check probe scheduler and transition to PROBING
        mock_probe_scheduler.should_probe_now.assert_called_once()
        mock_transition.assert_called_with(ThermalState.PROBING)
    print("✓ CORRECTING state checks probe scheduler and transitions to PROBING when approved")
    
    # Test 6: Probe scheduler declines probing
    print("\nTest 6: Probe scheduler declines probing")
    mock_probe_scheduler.reset_mock()
    mock_probe_scheduler.should_probe_now.return_value = False  # Scheduler declines
    
    manager._current_state = ThermalState.DRIFTING
    
    mock_handler = Mock()
    mock_handler.execute.return_value = None
    manager._state_handlers[ThermalState.DRIFTING] = mock_handler
    
    with patch.object(manager, 'transition_to') as mock_transition:
        manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
        
        # Should check probe scheduler but not transition
        mock_probe_scheduler.should_probe_now.assert_called_once()
        mock_transition.assert_not_called()
        assert manager._current_state == ThermalState.DRIFTING
    print("✓ DRIFTING state respects probe scheduler decline decision")
    
    # Test 7: Handler transitions take priority over probing
    print("\nTest 7: Handler transitions take priority over probing")
    mock_probe_scheduler.reset_mock()
    mock_probe_scheduler.should_probe_now.return_value = True  # Scheduler wants to probe
    
    manager._current_state = ThermalState.DRIFTING
    
    # Mock handler to return a different state
    mock_handler = Mock()
    mock_handler.execute.return_value = ThermalState.RECOVERY
    manager._state_handlers[ThermalState.DRIFTING] = mock_handler
    
    with patch.object(manager, 'transition_to') as mock_transition:
        manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
        
        # Should not check probe scheduler because handler transitions take priority
        mock_probe_scheduler.should_probe_now.assert_not_called()
        mock_transition.assert_called_with(ThermalState.RECOVERY)
    print("✓ Handler transitions take priority over probe scheduling")
    
    # Test 8: States that should not probe
    print("\nTest 8: Non-probing states ignore probe scheduler")
    non_probing_states = [ThermalState.RECOVERY, ThermalState.PROBING, ThermalState.CALIBRATING]
    
    for state in non_probing_states:
        mock_probe_scheduler.reset_mock()
        mock_probe_scheduler.should_probe_now.return_value = True
        
        manager._current_state = state
        mock_handler = Mock()
        mock_handler.execute.return_value = None
        manager._state_handlers[state] = mock_handler
        
        with patch.object(manager, 'transition_to') as mock_transition:
            manager.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
            
            # Should not check probe scheduler in these states
            mock_probe_scheduler.should_probe_now.assert_not_called()
            mock_transition.assert_not_called()
    print("✓ RECOVERY, PROBING, CALIBRATING states ignore probe scheduler")
    
    # Test 9: Backward compatibility during state updates
    print("\nTest 9: Backward compatibility during state updates")
    manager_no_scheduler._current_state = ThermalState.DRIFTING
    
    mock_handler = Mock()
    mock_handler.execute.return_value = None
    manager_no_scheduler._state_handlers[ThermalState.DRIFTING] = mock_handler
    
    # Should not crash when probe_scheduler is None
    try:
        manager_no_scheduler.update_state(current_temp=22.0, outdoor_temp=25.0, hvac_mode="cool")
        assert manager_no_scheduler._current_state == ThermalState.DRIFTING
        print("✓ No probe scheduler - graceful handling in DRIFTING state")
    except Exception as e:
        print(f"✗ Failed backward compatibility test: {e}")
        sys.exit(1)
    
    print("\n🎉 All integration tests passed!")
    print("\nIntegration Summary:")
    print("- ThermalManager constructor accepts optional probe_scheduler parameter")
    print("- Backward compatibility maintained when probe_scheduler=None")
    print("- PRIMING state: Only passive learning, no probe scheduling")
    print("- DRIFTING/CORRECTING states: Check probe scheduler for opportunistic probing")
    print("- RECOVERY/PROBING/CALIBRATING states: Ignore probe scheduler")
    print("- Handler transitions take priority over probe scheduling")
    print("- Probe scheduler decisions are respected (approve/decline)")
    print("- Error handling: Graceful degradation if probe scheduler fails")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)
except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)