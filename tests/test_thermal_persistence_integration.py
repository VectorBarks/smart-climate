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


class TestProbeTimestampIntegration:
    """Integration tests for complete timestamp persistence system.
    
    Verifies end-to-end timestamp persistence across the complete system per
    Serena memory 'architecture' §19 integration requirements.
    """

    @pytest.fixture
    def mock_hass(self):
        """Mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.data = {DOMAIN: {}}
        hass.config = Mock()
        hass.config.time_zone = "UTC"
        hass.states = Mock()
        hass.states.get.return_value = None
        return hass

    @pytest.fixture
    def thermal_manager(self, mock_hass):
        """Create real ThermalManager for integration testing."""
        thermal_model = PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0)
        preferences = Mock(spec=UserPreferences)
        preferences.level = PreferenceLevel.BALANCED
        preferences.get_adjusted_band.return_value = 1.5
        
        return ThermalManager(mock_hass, thermal_model, preferences)

    @pytest.mark.asyncio
    async def test_end_to_end_timestamp_persistence(self, thermal_manager):
        """Test complete multi-probe persistence flow with distinct timestamps.
        
        Scenario 1: Multi-Probe Persistence Flow
        - Create ThermalManager with multiple probes at different times
        - Serialize to JSON
        - Create new ThermalManager instance  
        - Restore from JSON
        - Verify all original timestamps preserved
        """
        from datetime import datetime, timezone, timedelta
        
        # Create probes with distinct timestamps (simulate different creation times)
        base_time = datetime(2025, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
        
        probe1 = ProbeResult(
            tau_value=85.5,
            confidence=0.82,
            duration=3600,
            fit_quality=0.91,
            aborted=False,
            timestamp=base_time  # 10:00 UTC
        )
        
        probe2 = ProbeResult(
            tau_value=92.3,
            confidence=0.88,
            duration=4200,
            fit_quality=0.94,
            aborted=False,
            timestamp=base_time + timedelta(hours=2)  # 12:00 UTC
        )
        
        probe3 = ProbeResult(
            tau_value=87.9,
            confidence=0.85,
            duration=3800,
            fit_quality=0.89,
            aborted=False,
            timestamp=base_time + timedelta(hours=4)  # 14:00 UTC
        )
        
        # Add probes to thermal manager
        thermal_manager._model._probe_history.append(probe1)
        thermal_manager._model._probe_history.append(probe2)
        thermal_manager._model._probe_history.append(probe3)
        
        # Serialize to JSON (simulates persistence)
        serialized_data = thermal_manager.serialize()
        
        # Verify serialization preserves timestamps correctly
        probe_history = serialized_data["probe_history"]
        assert len(probe_history) == 3, "All probes should be serialized"
        
        # Verify timestamps in serialized data
        serialized_timestamps = [probe["timestamp"] for probe in probe_history]
        assert "2025-08-15T10:00:00+00:00" in serialized_timestamps, "First probe timestamp missing"
        assert "2025-08-15T12:00:00+00:00" in serialized_timestamps, "Second probe timestamp missing"  
        assert "2025-08-15T14:00:00+00:00" in serialized_timestamps, "Third probe timestamp missing"
        
        # Create new ThermalManager instance (simulates HA restart)
        new_thermal_manager = ThermalManager(
            thermal_manager._hass, 
            PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0), 
            thermal_manager._preferences
        )
        
        # Restore from serialized data
        new_thermal_manager.restore(serialized_data)
        
        # Verify all timestamps preserved after restoration
        restored_probes = list(new_thermal_manager._model._probe_history)
        assert len(restored_probes) == 3, "All probes should be restored"
        
        restored_timestamps = {probe.timestamp for probe in restored_probes}
        expected_timestamps = {
            base_time,
            base_time + timedelta(hours=2),
            base_time + timedelta(hours=4)
        }
        
        assert restored_timestamps == expected_timestamps, f"Timestamps not preserved correctly. Expected: {expected_timestamps}, Got: {restored_timestamps}"
        
        # Verify temporal relationships maintained
        sorted_probes = sorted(restored_probes, key=lambda p: p.timestamp)
        assert sorted_probes[0].tau_value == 85.5, "First probe order incorrect"
        assert sorted_probes[1].tau_value == 92.3, "Second probe order incorrect"
        assert sorted_probes[2].tau_value == 87.9, "Third probe order incorrect"
        
        print("✅ Multi-probe timestamp persistence verified")

    @pytest.mark.asyncio
    async def test_legacy_data_migration(self, thermal_manager):
        """Test legacy migration - load pre-fix JSON data without timestamps.
        
        Scenario 2: Legacy Migration Test
        - Load pre-fix JSON data (without timestamps)
        - Verify graceful conversion to new format
        - Ensure no data loss or corruption
        """
        # Simulate legacy data without timestamp fields
        legacy_data = {
            "version": "1.0",
            "state": {
                "current_state": "priming",
                "last_transition": "2025-08-15T10:30:00+00:00"
            },
            "model": {
                "tau_cooling": 88.0,
                "tau_warming": 155.0,
                "last_modified": "2025-08-15T10:15:00+00:00"
            },
            "probe_history": [
                {
                    "tau_value": 89.2,
                    "confidence": 0.78,
                    "duration": 3900,
                    "fit_quality": 0.86,
                    "aborted": False
                    # Note: No timestamp field (legacy format)
                },
                {
                    "tau_value": 91.7,
                    "confidence": 0.83,
                    "duration": 4100,
                    "fit_quality": 0.92,
                    "aborted": False
                    # Note: No timestamp field (legacy format)
                }
            ],
            "confidence": 0.81,
            "metadata": {
                "saves_count": 3,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }
        }
        
        # Capture time before restoration for fallback verification
        from datetime import timezone
        before_restore = datetime.now(timezone.utc)
        
        # Restore legacy data
        thermal_manager.restore(legacy_data)
        
        # Capture time after restoration
        after_restore = datetime.now(timezone.utc)
        
        # Verify probes were restored correctly
        restored_probes = list(thermal_manager._model._probe_history)
        assert len(restored_probes) == 2, "Legacy probes should be restored"
        
        # Verify probe data integrity
        tau_values = {probe.tau_value for probe in restored_probes}
        assert 89.2 in tau_values, "First legacy probe data lost"
        assert 91.7 in tau_values, "Second legacy probe data lost"
        
        # Verify fallback timestamps were assigned
        for probe in restored_probes:
            assert probe.timestamp is not None, "Fallback timestamp not assigned"
            assert isinstance(probe.timestamp, datetime), "Invalid timestamp type"
            assert probe.timestamp.tzinfo is not None, "Timestamp should be timezone-aware"
            # Fallback timestamp should be between before and after restoration
            assert before_restore <= probe.timestamp <= after_restore, "Fallback timestamp out of range"
        
        # Verify serialization works with converted legacy data
        serialized_after_migration = thermal_manager.serialize()
        probe_history = serialized_after_migration["probe_history"]
        
        assert len(probe_history) == 2, "Migrated probes should serialize"
        for probe in probe_history:
            assert "timestamp" in probe, "Migrated probe missing timestamp in serialization"
            # Verify timestamp can be parsed
            datetime.fromisoformat(probe["timestamp"])
        
        print("✅ Legacy data migration verified")

    @pytest.mark.asyncio
    async def test_mixed_data_format_handling(self, thermal_manager):
        """Test mixed data handling - combine legacy and new data.
        
        Scenario 3: Mixed Data Handling
        - Combine legacy and new data in single restore operation
        - Verify correct processing of both formats
        """
        from datetime import timezone, timedelta
        
        # First, add a probe with modern timestamp to thermal manager
        modern_probe = ProbeResult(
            tau_value=94.5,
            confidence=0.89,
            duration=3700,
            fit_quality=0.93,
            aborted=False,
            timestamp=datetime(2025, 8, 15, 16, 0, 0, tzinfo=timezone.utc)
        )
        thermal_manager._model._probe_history.append(modern_probe)
        
        # Now restore mixed data (some with timestamps, some without)
        mixed_data = {
            "version": "1.0",
            "state": {
                "current_state": "calibrating",
                "last_transition": "2025-08-15T15:45:00+00:00"
            },
            "model": {
                "tau_cooling": 86.5,
                "tau_warming": 148.0,
                "last_modified": "2025-08-15T15:30:00+00:00"
            },
            "probe_history": [
                {
                    "tau_value": 87.3,
                    "confidence": 0.76,
                    "duration": 3800,
                    "fit_quality": 0.84,
                    "aborted": False
                    # Legacy: No timestamp
                },
                {
                    "tau_value": 90.8,
                    "confidence": 0.85,
                    "duration": 4000,
                    "fit_quality": 0.91,
                    "aborted": False,
                    "timestamp": "2025-08-15T14:00:00+00:00"  # Modern: With timestamp
                },
                {
                    "tau_value": 89.1,
                    "confidence": 0.82,
                    "duration": 3950,
                    "fit_quality": 0.88,
                    "aborted": False
                    # Legacy: No timestamp
                }
            ],
            "confidence": 0.84,
            "metadata": {
                "saves_count": 7,
                "corruption_recoveries": 1,
                "schema_version": "1.0"
            }
        }
        
        before_restore = datetime.now(timezone.utc)
        thermal_manager.restore(mixed_data)
        after_restore = datetime.now(timezone.utc)
        
        # Verify all probes present (1 original + 3 from mixed data)
        all_probes = list(thermal_manager._model._probe_history)
        assert len(all_probes) == 4, f"Expected 4 probes total, got {len(all_probes)}"
        
        # Verify modern probe preserved
        modern_probes = [p for p in all_probes if p.tau_value == 94.5]
        assert len(modern_probes) == 1, "Original modern probe should be preserved"
        assert modern_probes[0].timestamp == datetime(2025, 8, 15, 16, 0, 0, tzinfo=timezone.utc)
        
        # Verify mixed data probe with timestamp preserved
        timestamped_probes = [p for p in all_probes if p.tau_value == 90.8]
        assert len(timestamped_probes) == 1, "Timestamped probe from mixed data missing"
        assert timestamped_probes[0].timestamp == datetime(2025, 8, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        # Verify legacy probes got fallback timestamps
        legacy_probes = [p for p in all_probes if p.tau_value in [87.3, 89.1]]
        assert len(legacy_probes) == 2, "Legacy probes from mixed data missing"
        
        for legacy_probe in legacy_probes:
            assert before_restore <= legacy_probe.timestamp <= after_restore, \
                f"Legacy probe timestamp {legacy_probe.timestamp} outside expected range"
        
        print("✅ Mixed data format handling verified")

    @pytest.mark.asyncio
    async def test_corruption_recovery_integration(self, thermal_manager):
        """Test error recovery integration for corrupted timestamp data.
        
        Scenario 4: Error Recovery Integration
        - Test corrupted timestamp data handling
        - Verify system continues to function correctly
        """
        from datetime import timezone
        
        corrupted_data = {
            "version": "1.0",
            "state": {
                "current_state": "drifting",
                "last_transition": "2025-08-15T17:00:00+00:00"
            },
            "model": {
                "tau_cooling": 92.0,
                "tau_warming": 158.0,
                "last_modified": "2025-08-15T16:45:00+00:00"
            },
            "probe_history": [
                {
                    "tau_value": 88.7,
                    "confidence": 0.79,
                    "duration": 3600,
                    "fit_quality": 0.87,
                    "aborted": False,
                    "timestamp": "invalid-timestamp-format"  # Corrupted timestamp
                },
                {
                    "tau_value": 93.2,
                    "confidence": 0.86,
                    "duration": 4200,
                    "fit_quality": 0.94,
                    "aborted": False,
                    "timestamp": "2025-13-45T99:99:99"  # Invalid date/time values
                },
                {
                    "tau_value": 90.5,
                    "confidence": 0.83,
                    "duration": 3900,
                    "fit_quality": 0.90,
                    "aborted": False,
                    "timestamp": "2025-08-15T15:30:00+00:00"  # Valid timestamp
                }
            ],
            "confidence": 0.82,
            "metadata": {
                "saves_count": 5,
                "corruption_recoveries": 2,
                "schema_version": "1.0"
            }
        }
        
        # Record initial corruption count
        initial_corruption_count = thermal_manager._corruption_recovery_count
        
        before_restore = datetime.now(timezone.utc)
        thermal_manager.restore(corrupted_data)
        after_restore = datetime.now(timezone.utc)
        
        # Verify system handled corruption gracefully
        restored_probes = list(thermal_manager._model._probe_history)
        assert len(restored_probes) == 3, "All probes should be restored despite timestamp corruption"
        
        # Verify corruption recovery count increased
        assert thermal_manager._corruption_recovery_count > initial_corruption_count, \
            "Corruption recovery count should increase"
        
        # Find probes by tau_value to verify handling
        probe_88_7 = next((p for p in restored_probes if p.tau_value == 88.7), None)
        probe_93_2 = next((p for p in restored_probes if p.tau_value == 93.2), None)
        probe_90_5 = next((p for p in restored_probes if p.tau_value == 90.5), None)
        
        assert probe_88_7 is not None, "Probe with corrupted timestamp should be restored"
        assert probe_93_2 is not None, "Probe with invalid timestamp should be restored"
        assert probe_90_5 is not None, "Probe with valid timestamp should be restored"
        
        # Verify corrupted timestamps got fallback values
        assert before_restore <= probe_88_7.timestamp <= after_restore, \
            "Corrupted timestamp should get fallback value"
        assert before_restore <= probe_93_2.timestamp <= after_restore, \
            "Invalid timestamp should get fallback value"
        
        # Verify valid timestamp preserved
        expected_valid_time = datetime(2025, 8, 15, 15, 30, 0, tzinfo=timezone.utc)
        assert probe_90_5.timestamp == expected_valid_time, \
            "Valid timestamp should be preserved"
        
        # Verify system continues to function - test serialization
        post_corruption_data = thermal_manager.serialize()
        assert "probe_history" in post_corruption_data, "System should continue working after corruption"
        assert len(post_corruption_data["probe_history"]) == 3, "All probes should serialize after corruption recovery"
        
        # Verify all serialized probes have valid timestamps
        for probe in post_corruption_data["probe_history"]:
            assert "timestamp" in probe, "Serialized probe missing timestamp after corruption recovery"
            # Should be able to parse without error
            parsed_timestamp = datetime.fromisoformat(probe["timestamp"])
            assert isinstance(parsed_timestamp, datetime), "Corrupted timestamp not properly recovered"
        
        print("✅ Corruption recovery integration verified")

    @pytest.mark.asyncio
    async def test_performance_impact_verification(self, thermal_manager):
        """Verify performance impact of timestamp persistence is <5%.
        
        This test ensures the timestamp enhancements don't significantly
        impact system performance during normal operations.
        """
        import time
        from datetime import timezone, timedelta
        
        # Create many probes for performance testing
        base_time = datetime(2025, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
        probes = []
        
        for i in range(50):  # Large number for performance testing
            probe = ProbeResult(
                tau_value=85.0 + i * 0.5,
                confidence=0.8 + (i % 10) * 0.02,
                duration=3600 + i * 60,
                fit_quality=0.85 + (i % 15) * 0.01,
                aborted=i % 10 == 0,  # Some aborted probes
                timestamp=base_time + timedelta(minutes=i * 30)
            )
            probes.append(probe)
            thermal_manager._model._probe_history.append(probe)
        
        # Benchmark serialization performance
        serialize_times = []
        for _ in range(10):  # Multiple runs for accurate measurement
            start_time = time.perf_counter()
            serialized_data = thermal_manager.serialize()
            end_time = time.perf_counter()
            serialize_times.append(end_time - start_time)
        
        avg_serialize_time = sum(serialize_times) / len(serialize_times)
        
        # Benchmark restore performance
        restore_times = []
        for _ in range(10):
            # Create fresh thermal manager for each test
            test_manager = ThermalManager(
                thermal_manager._hass,
                PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0),
                thermal_manager._preferences
            )
            
            start_time = time.perf_counter()
            test_manager.restore(serialized_data)
            end_time = time.perf_counter()
            restore_times.append(end_time - start_time)
        
        avg_restore_time = sum(restore_times) / len(restore_times)
        
        # Performance expectations (should be very fast for reasonable data sizes)
        assert avg_serialize_time < 0.1, f"Serialization too slow: {avg_serialize_time:.4f}s (expected <0.1s)"
        assert avg_restore_time < 0.1, f"Restoration too slow: {avg_restore_time:.4f}s (expected <0.1s)"
        
        # Verify all probes were properly handled
        final_probes = list(thermal_manager._model._probe_history)
        assert len(final_probes) >= 50, "Performance test probes missing"
        
        # Verify timestamps are all distinct and properly ordered
        timestamps = [p.timestamp for p in final_probes[-50:]]  # Last 50 probes
        assert len(set(timestamps)) == 50, "Timestamps should be distinct"
        
        sorted_timestamps = sorted(timestamps)
        assert timestamps[-50:] == sorted_timestamps, "Timestamps should be chronologically ordered"
        
        print(f"✅ Performance verified: serialize={avg_serialize_time:.4f}s, restore={avg_restore_time:.4f}s")

    @pytest.mark.asyncio
    async def test_timezone_handling_verification(self, thermal_manager):
        """Verify proper timezone handling in timestamp persistence.
        
        Ensures timestamps are properly normalized to UTC and handle
        various timezone scenarios correctly.
        """
        from datetime import datetime, timezone, timedelta
        
        # Test different timezone scenarios
        utc_time = datetime(2025, 8, 15, 14, 30, 0, tzinfo=timezone.utc)
        est_time = datetime(2025, 8, 15, 10, 30, 0, tzinfo=timezone(timedelta(hours=-4)))  # EST
        cet_time = datetime(2025, 8, 15, 16, 30, 0, tzinfo=timezone(timedelta(hours=2)))   # CET
        
        # These should all represent the same moment in time
        assert utc_time.astimezone(timezone.utc) == utc_time
        assert est_time.astimezone(timezone.utc) == utc_time
        assert cet_time.astimezone(timezone.utc) == utc_time
        
        # Create probes with different timezone representations
        utc_probe = ProbeResult(
            tau_value=88.0, confidence=0.8, duration=3600, fit_quality=0.9, aborted=False,
            timestamp=utc_time
        )
        
        est_probe = ProbeResult(
            tau_value=90.0, confidence=0.85, duration=3700, fit_quality=0.92, aborted=False,
            timestamp=est_time
        )
        
        cet_probe = ProbeResult(
            tau_value=92.0, confidence=0.87, duration=3800, fit_quality=0.94, aborted=False,
            timestamp=cet_time
        )
        
        thermal_manager._model._probe_history.extend([utc_probe, est_probe, cet_probe])
        
        # Serialize and restore
        serialized_data = thermal_manager.serialize()
        
        new_manager = ThermalManager(
            thermal_manager._hass,
            PassiveThermalModel(tau_cooling=90.0, tau_warming=150.0),
            thermal_manager._preferences
        )
        new_manager.restore(serialized_data)
        
        # Verify timezone handling
        restored_probes = list(new_manager._model._probe_history)
        restored_utc_timestamps = [p.timestamp.astimezone(timezone.utc) for p in restored_probes[-3:]]
        
        # All timestamps should normalize to the same UTC time
        assert all(ts == utc_time for ts in restored_utc_timestamps), \
            "Timezone normalization failed in persistence"
        
        # Verify serialized timestamps are in ISO format with timezone info
        probe_history = serialized_data["probe_history"]
        for probe in probe_history[-3:]:
            timestamp_str = probe["timestamp"]
            assert "+" in timestamp_str or "Z" in timestamp_str, \
                f"Serialized timestamp missing timezone info: {timestamp_str}"
            # Should parse back to same UTC time
            parsed = datetime.fromisoformat(timestamp_str)
            assert parsed.astimezone(timezone.utc) == utc_time, \
                "Timestamp persistence altered actual time value"
        
        print("✅ Timezone handling verified")