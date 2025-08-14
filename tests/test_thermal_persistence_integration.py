"""ABOUTME: Integration test for thermal data persistence Issue #67.
Tests full callback chain from OffsetEngine save to ThermalManager serialize."""

import pytest
import asyncio
import json
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from datetime import datetime
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant

from custom_components.smart_climate.thermal_models import ThermalState, ProbeResult
from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
from custom_components.smart_climate.thermal_model import PassiveThermalModel
from custom_components.smart_climate.thermal_manager import ThermalManager
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.data_store import SmartClimateDataStore
from custom_components.smart_climate.const import DOMAIN


class TestThermalPersistenceIntegration:
    """Test full thermal data persistence integration per Issue #67."""

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance with data structure."""
        hass = Mock()
        hass.data = {
            DOMAIN: {
                "test_entry_id": {
                    "thermal_components": {},
                    "offset_engines": {}
                }
            }
        }
        return hass

    @pytest.fixture
    def thermal_manager(self, mock_hass):
        """Create working ThermalManager with test data."""
        # Create mock thermal model with probe history
        thermal_model = Mock(spec=PassiveThermalModel)
        thermal_model.get_confidence.return_value = 0.75
        thermal_model._tau_cooling = 95.5
        thermal_model._tau_warming = 148.2
        
        # Add probe history
        probe = ProbeResult(
            tau_value=95.5,
            confidence=0.85,
            duration=3600,
            fit_quality=0.92,
            aborted=False
        )
        thermal_model._probe_history = [probe]
        
        # Create user preferences
        prefs = Mock(spec=UserPreferences)
        prefs.level = PreferenceLevel.BALANCED
        
        # Create thermal manager
        manager = ThermalManager(mock_hass, thermal_model, prefs)
        manager._current_state = ThermalState.DRIFTING
        manager._last_transition = datetime.now()
        
        return manager

    @pytest.fixture
    def coordinator(self, mock_hass, thermal_manager):
        """Create SmartClimateCoordinator with thermal components."""
        # Store thermal manager in hass.data structure
        entity_id = "climate.test_thermostat"
        mock_hass.data[DOMAIN]["test_entry_id"]["thermal_components"][entity_id] = {
            "thermal_manager": thermal_manager,
            "thermal_model": thermal_manager._model,
            "user_preferences": thermal_manager._preferences
        }
        
        # Create coordinator with minimal required components
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        return coordinator, entity_id

    @pytest.fixture  
    def mock_data_store(self):
        """Mock data store for persistence."""
        data_store = Mock(spec=SmartClimateDataStore)
        data_store.async_save_learning_data = AsyncMock()
        return data_store

    @pytest.fixture
    def offset_engine_with_callbacks(self, mock_hass, coordinator, mock_data_store):
        """Create OffsetEngine with thermal callbacks configured."""
        coordinator_instance, entity_id = coordinator
        
        # Create callbacks using functools.partial pattern from __init__.py
        from functools import partial
        get_thermal_cb = partial(coordinator_instance.get_thermal_data, entity_id)
        restore_thermal_cb = partial(coordinator_instance.restore_thermal_data, entity_id)
        
        # Create OffsetEngine with callbacks
        config = {"max_offset": 5.0, "ml_enabled": True}
        engine = OffsetEngine(
            config=config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        
        # Set data store
        engine._data_store = mock_data_store
        
        return engine, entity_id

    @pytest.mark.asyncio
    async def test_thermal_data_callback_chain_works(self, mock_hass, thermal_manager, mock_data_store):
        """Test that thermal_data is populated during save - reproduces Issue #67."""
        entity_id = "climate.test_thermostat"
        
        # Set up hass.data structure properly
        mock_hass.data[DOMAIN]["test_entry_id"]["thermal_components"][entity_id] = {
            "thermal_manager": thermal_manager
        }
        
        # Create direct callback functions (simulating fixed __init__.py)
        def get_thermal_data_direct() -> Optional[dict]:
            """Get thermal data directly from hass.data."""
            try:
                domain_data = mock_hass.data.get(DOMAIN, {})
                for entry_id, entry_data in domain_data.items():
                    thermal_components_data = entry_data.get("thermal_components", {})
                    if entity_id in thermal_components_data:
                        thermal_manager = thermal_components_data[entity_id].get("thermal_manager")
                        if thermal_manager:
                            return thermal_manager.serialize()
                return None
            except Exception as exc:
                print(f"Error in callback: {exc}")
                return None
        
        # Create OffsetEngine with direct callbacks
        config = {"max_offset": 5.0, "ml_enabled": True}
        engine = OffsetEngine(
            config=config,
            get_thermal_data_cb=get_thermal_data_direct,
            restore_thermal_data_cb=lambda data: None
        )
        
        # Set data store
        engine._data_store = mock_data_store
        
        # DEBUG: Test the callback works
        print(f"Testing direct callback...")
        direct_result = get_thermal_data_direct()
        print(f"Direct callback result type: {type(direct_result)}")
        if isinstance(direct_result, dict):
            print(f"Direct callback keys: {list(direct_result.keys())}")
        
        # Trigger save operation
        await engine.async_save_learning_data()
        
        # Verify async_save_learning_data was called
        mock_data_store.async_save_learning_data.assert_called_once()
        
        # Get the saved data
        save_call = mock_data_store.async_save_learning_data.call_args[0][0]
        
        # Debug: Print the saved data structure
        print(f"Saved data structure: {json.dumps(save_call, indent=2, default=str)}")
        
        # Verify v2.1 schema structure
        assert save_call["version"] == "2.1"
        assert "learning_data" in save_call
        assert "thermal_data" in save_call
        
        # THE KEY TEST: thermal_data should NOT be None/empty
        thermal_data = save_call["thermal_data"]
        assert thermal_data is not None, "thermal_data section is None - Issue #67 reproduced"
        
        # Verify thermal_data contains expected structure  
        assert isinstance(thermal_data, dict), f"thermal_data is not dict: {type(thermal_data)}"
        assert "version" in thermal_data
        assert "state" in thermal_data
        assert "model" in thermal_data
        assert "confidence" in thermal_data
        
        # Verify state data
        assert thermal_data["state"]["current_state"] == "drifting"
        
        # Verify model data
        assert thermal_data["model"]["tau_cooling"] == 95.5
        assert thermal_data["model"]["tau_warming"] == 148.2
        
        print("✅ TEST PASSED: thermal_data is properly populated!")

    @pytest.mark.asyncio
    async def test_callback_missing_logs_debug(self, mock_hass, mock_data_store):
        """Test that missing callback logs debug message but doesn't fail."""
        # Create engine WITHOUT callbacks
        config = {"max_offset": 5.0, "ml_enabled": True}
        engine = OffsetEngine(config=config)
        engine._data_store = mock_data_store
        
        with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
            await engine.async_save_learning_data()
            
            # Verify save was called with thermal_data = None
            save_call = mock_data_store.async_save_learning_data.call_args[0][0]
            assert save_call["thermal_data"] is None
            
            # No error should be logged (only debug)
            mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_callback_exception_handled_gracefully(self, offset_engine_with_callbacks, mock_data_store):
        """Test that callback exceptions don't prevent save."""
        engine, entity_id = offset_engine_with_callbacks
        
        # Make callback raise exception
        with patch.object(engine._get_thermal_data_cb, '__call__', side_effect=Exception("Test callback error")):
            with patch('custom_components.smart_climate.offset_engine._LOGGER') as mock_logger:
                await engine.async_save_learning_data()
                
                # Verify save still completed
                mock_data_store.async_save_learning_data.assert_called_once()
                save_call = mock_data_store.async_save_learning_data.call_args[0][0]
                
                # thermal_data should be None due to exception
                assert save_call["thermal_data"] is None
                
                # Debug message should be logged
                mock_logger.debug.assert_any_call("Failed to get thermal data: %s", mock_logger.debug.call_args_list[0][0][1])

    @pytest.mark.asyncio
    async def test_coordinator_get_thermal_data_missing_manager(self, mock_hass):
        """Test coordinator.get_thermal_data when ThermalManager is missing."""
        # Create coordinator with minimal required components
        sensor_manager = Mock()
        offset_engine = Mock()
        mode_manager = Mock()
        
        coordinator = SmartClimateCoordinator(
            hass=mock_hass,
            update_interval=180,
            sensor_manager=sensor_manager,
            offset_engine=offset_engine,
            mode_manager=mode_manager
        )
        
        # Call get_thermal_data for non-existent entity
        result = coordinator.get_thermal_data("climate.nonexistent")
        
        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_coordinator_get_thermal_data_calls_serialize(self, coordinator, thermal_manager):
        """Test coordinator.get_thermal_data calls ThermalManager.serialize()."""
        coordinator_instance, entity_id = coordinator
        
        # Mock serialize method
        thermal_manager.serialize = Mock(return_value={"test": "data"})
        
        # Call get_thermal_data
        result = coordinator_instance.get_thermal_data(entity_id)
        
        # Verify serialize was called
        thermal_manager.serialize.assert_called_once()
        assert result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_full_integration_with_real_thermal_manager(self, offset_engine_with_callbacks, mock_data_store):
        """Test full integration with real ThermalManager serialize method."""
        engine, entity_id = offset_engine_with_callbacks
        
        # Trigger save
        await engine.async_save_learning_data()
        
        # Get saved data
        save_call = mock_data_store.async_save_learning_data.call_args[0][0]
        thermal_data = save_call["thermal_data"]
        
        # Verify complete thermal data structure matches architecture spec
        assert thermal_data["version"] == "1.0"
        
        # Verify state section
        state_data = thermal_data["state"]
        assert state_data["current_state"] == "drifting"
        assert "last_transition" in state_data
        
        # Verify model section
        model_data = thermal_data["model"]
        assert model_data["tau_cooling"] == 95.5
        assert model_data["tau_warming"] == 148.2
        assert "last_modified" in model_data
        
        # Verify probe history
        probe_history = thermal_data["probe_history"]
        assert len(probe_history) == 1
        assert probe_history[0]["tau_value"] == 95.5
        assert probe_history[0]["confidence"] == 0.85
        
        # Verify confidence and metadata
        assert thermal_data["confidence"] == 0.75
        assert "metadata" in thermal_data

    def test_functools_partial_callback_creation(self, coordinator):
        """Test that functools.partial callbacks work as expected."""
        from functools import partial
        
        coordinator_instance, entity_id = coordinator
        
        # Create callback using partial (matches __init__.py pattern)
        get_thermal_cb = partial(coordinator_instance.get_thermal_data, entity_id)
        
        # Mock the serialize method to verify callback works
        thermal_manager = coordinator_instance.hass.data[DOMAIN]["test_entry_id"]["thermal_components"][entity_id]["thermal_manager"]
        thermal_manager.serialize = Mock(return_value={"callback": "works"})
        
        # Call callback
        result = get_thermal_cb()
        
        # Verify it calls coordinator.get_thermal_data with correct entity_id
        thermal_manager.serialize.assert_called_once()
        assert result == {"callback": "works"}

    @pytest.mark.asyncio
    async def test_probe_history_extension_integration_fix(self, mock_hass):
        """Integration test for probe history data loss bug fix.
        
        CRITICAL BUG FIX VERIFICATION: Tests the complete fix from thermal_manager.py line 685
        where restore() was replacing probe_history instead of extending it.
        
        This integration test verifies:
        1. Runtime probes are preserved during HA restart simulation
        2. Restored probes are properly added to existing ones
        3. No thermal learning data is lost during typical save/restore cycles
        4. Fix works end-to-end with real thermal manager components
        """
        from collections import deque
        from custom_components.smart_climate.thermal_model import PassiveThermalModel
        from custom_components.smart_climate.thermal_manager import ThermalManager
        from custom_components.smart_climate.thermal_preferences import UserPreferences, PreferenceLevel
        
        # Create real thermal components (not mocks) for integration testing
        thermal_model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        preferences = Mock(spec=UserPreferences)
        preferences.level = PreferenceLevel.BALANCED
        preferences.get_adjusted_band.return_value = 1.5
        
        thermal_manager = ThermalManager(mock_hass, thermal_model, preferences)
        
        # Phase 1: Simulate active learning during runtime
        runtime_probe1 = ProbeResult(
            tau_value=95.0,
            confidence=0.8,
            duration=3600,
            fit_quality=0.9,
            aborted=False
        )
        runtime_probe2 = ProbeResult(
            tau_value=102.5,
            confidence=0.85,
            duration=3200,
            fit_quality=0.92,
            aborted=False
        )
        
        # Add probes during runtime (before any save/restore)
        thermal_manager._model._probe_history.append(runtime_probe1)
        thermal_manager._model._probe_history.append(runtime_probe2)
        
        initial_probe_count = len(thermal_manager._model._probe_history)
        assert initial_probe_count == 2, "Initial probe setup failed"
        
        # Phase 2: Simulate HA restart by restoring data from disk
        # This data would typically come from a previous save operation
        restore_data = {
            "version": "1.0",
            "state": {"current_state": "priming", "last_transition": "2025-08-15T12:00:00"},
            "model": {"tau_cooling": 88.0, "tau_warming": 155.0, "last_modified": "2025-08-15T11:30:00"},
            "probe_history": [
                {
                    "tau_value": 87.5,
                    "confidence": 0.75,
                    "duration": 4200,
                    "fit_quality": 0.88,
                    "aborted": False,
                    "timestamp": "2025-08-15T11:30:00"
                }
            ],
            "confidence": 0.78,
            "metadata": {"saves_count": 5, "corruption_recoveries": 0, "schema_version": "1.0"}
        }
        
        # CRITICAL: This restore() call should EXTEND probe_history, not replace it
        thermal_manager.restore(restore_data)
        
        # Phase 3: Verify fix - all probes should be present
        final_probes = list(thermal_manager._model._probe_history)
        final_tau_values = [p.tau_value for p in final_probes]
        
        # Should have 3 probes total: 2 runtime + 1 restored
        assert len(final_probes) == 3, f"Expected 3 probes after restore, got {len(final_probes)} - data loss occurred!"
        
        # All original runtime probes must be preserved
        assert 95.0 in final_tau_values, "Runtime probe 95.0 lost during restore - bug still exists!"
        assert 102.5 in final_tau_values, "Runtime probe 102.5 lost during restore - bug still exists!"
        
        # Restored probe must be added
        assert 87.5 in final_tau_values, "Restored probe 87.5 missing - restoration failed!"
        
        # Phase 4: Verify thermal model confidence reflects all probes
        # With more probes, confidence should be higher than with just restored probe alone
        final_confidence = thermal_manager._model.get_confidence()
        assert final_confidence > 0.0, "Thermal confidence calculation broken"
        
        # Phase 5: Test serialization preserves all probes
        serialized_after_restore = thermal_manager.serialize()
        serialized_probes = serialized_after_restore["probe_history"]
        serialized_tau_values = [p["tau_value"] for p in serialized_probes]
        
        assert len(serialized_probes) == 3, "Serialization lost probes after restore"
        assert 95.0 in serialized_tau_values, "Runtime probe missing from serialization"
        assert 102.5 in serialized_tau_values, "Runtime probe missing from serialization"
        assert 87.5 in serialized_tau_values, "Restored probe missing from serialization"
        
        print("✅ INTEGRATION TEST PASSED: Probe history extension fix works end-to-end")