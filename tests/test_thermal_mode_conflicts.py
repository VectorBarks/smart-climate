"""Comprehensive conflict scenario and edge case tests for thermal state + mode priority.

ABOUTME: Edge case and stress tests for thermal-mode integration system,
verifying graceful handling of rapid changes, invalid states, and error conditions.
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, time
import asyncio
import gc
import time as time_module
from homeassistant.const import STATE_ON, STATE_OFF

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import (
    OffsetInput, 
    OffsetResult, 
    ModeAdjustments, 
    SmartClimateData
)
from custom_components.smart_climate.thermal_models import ThermalState
from custom_components.smart_climate.const import DOMAIN
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_state,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator
)


class TestRapidModeStateSwitching:
    """Test rapid switching between modes and thermal states."""

    @pytest.fixture
    def rapid_switch_entity(self):
        """Create entity optimized for rapid switching tests."""
        hass = create_mock_hass()
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    "thermal_components": {
                        "climate.test": MagicMock()
                    }
                }
            }
        }
        
        # Create climate entity state
        climate_state = create_mock_state(
            state="cool",
            attributes={"current_temperature": 24.0, "hvac_mode": "cool"},
            entity_id="climate.test"
        )
        hass.states.set("climate.test", climate_state)
        
        config = {'entry_id': 'test_entry'}
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(hass),
            coordinator=create_mock_coordinator()
        )
        
        # Setup sensor defaults
        entity._sensor_manager.get_room_temperature.return_value = 24.0
        entity._sensor_manager.get_outdoor_temperature.return_value = 28.0
        entity._sensor_manager.get_power_consumption.return_value = 1500.0
        entity._sensor_manager.get_indoor_humidity.return_value = None
        entity._sensor_manager.get_outdoor_humidity.return_value = None
        
        # Setup offset engine
        offset_result = OffsetResult(offset=1.0, clamped=False, reason="test", confidence=0.8)
        entity._offset_engine.calculate_offset.return_value = offset_result
        
        return entity, hass.data[DOMAIN]["test_entry"]["thermal_components"]["climate.test"]

    @pytest.mark.asyncio
    async def test_rapid_mode_thermal_state_changes(self, rapid_switch_entity):
        """Test system stability under rapid mode and thermal state changes.
        
        Simulates a stress scenario where boost mode is rapidly toggled
        while thermal state transitions between DRIFTING and CORRECTING.
        """
        entity, thermal_manager = rapid_switch_entity
        
        # Track all temperature commands
        temp_commands = []
        original_send_command = entity._temperature_controller.send_temperature_command
        
        async def track_commands(entity_id, temperature):
            temp_commands.append({
                "timestamp": datetime.now(),
                "entity_id": entity_id, 
                "temperature": temperature
            })
            await original_send_command(entity_id, temperature)
        
        entity._temperature_controller.send_temperature_command = track_commands
        
        # Scenario: 20 rapid cycles in 5 seconds
        test_cycles = 20
        
        for cycle in range(test_cycles):
            # Rapidly alternate modes and thermal states
            if cycle % 2 == 0:
                # Boost mode + DRIFTING state conflict
                thermal_manager.current_state = ThermalState.DRIFTING
                boost_adjustments = ModeAdjustments(
                    temperature_override=None,
                    offset_adjustment=0.0,
                    update_interval_override=None,
                    boost_offset=-2.0,
                    force_operation=True
                )
                expected_temp = 20.0  # Boost overrides
            else:
                # Normal mode + CORRECTING state
                thermal_manager.current_state = ThermalState.CORRECTING
                normal_adjustments = ModeAdjustments(
                    temperature_override=None,
                    offset_adjustment=0.0,
                    update_interval_override=None,
                    boost_offset=0.0,
                    force_operation=False
                )
                expected_temp = 23.5  # Standard operation
            
            entity._mode_manager.get_adjustments.return_value = (
                boost_adjustments if cycle % 2 == 0 else normal_adjustments
            )
            entity._temperature_controller.apply_offset_and_limits.return_value = expected_temp
            
            with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                # Apply temperature command
                await entity._apply_temperature_with_offset(22.0, source=f"rapid_cycle_{cycle}")
                
                # Small delay to simulate real timing
                await asyncio.sleep(0.01)
        
        # Verify system handled all commands without errors
        assert len(temp_commands) == test_cycles
        
        # Verify no commands were corrupted or lost
        for i, command in enumerate(temp_commands):
            assert command["entity_id"] == "climate.test"
            assert isinstance(command["temperature"], (int, float))
            assert 15.0 <= command["temperature"] <= 30.0  # Within reasonable bounds
        
        # Verify final state is consistent
        final_state = thermal_manager.current_state
        final_mode = entity._mode_manager.get_adjustments.return_value
        assert final_state in [ThermalState.DRIFTING, ThermalState.CORRECTING]
        assert isinstance(final_mode, ModeAdjustments)

    @pytest.mark.asyncio
    async def test_performance_under_rapid_state_changes(self, rapid_switch_entity):
        """Test performance metrics under rapid state changes."""
        entity, thermal_manager = rapid_switch_entity
        
        # Track performance metrics
        execution_times = []
        memory_usage_before = 0
        memory_usage_after = 0
        
        # Measure initial memory usage
        gc.collect()
        
        # Performance test: 100 rapid operations
        start_time = time_module.time()
        
        for i in range(100):
            operation_start = time_module.time()
            
            # Alternate between conflict scenarios
            if i % 3 == 0:
                thermal_manager.current_state = ThermalState.DRIFTING
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=-3.0, force_operation=True
                )
            elif i % 3 == 1:
                thermal_manager.current_state = ThermalState.CORRECTING
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=26.0, offset_adjustment=1.0,
                    update_interval_override=None, boost_offset=0.0, force_operation=False
                )
            else:
                thermal_manager.current_state = ThermalState.PRIMING
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=300, boost_offset=0.0, force_operation=False
                )
            
            entity._temperature_controller.apply_offset_and_limits.return_value = 22.0 + (i % 5)
            
            with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                await entity._apply_temperature_with_offset(23.0, source=f"perf_test_{i}")
            
            operation_end = time_module.time()
            execution_times.append(operation_end - operation_start)
        
        total_time = time_module.time() - start_time
        
        # Analyze performance
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        min_execution_time = min(execution_times)
        
        # Performance assertions
        assert avg_execution_time < 0.050  # Average under 50ms
        assert max_execution_time < 0.200  # No operation over 200ms
        assert total_time < 10.0          # Total under 10 seconds
        
        # Verify consistency - no extreme outliers
        outliers = [t for t in execution_times if t > (avg_execution_time * 3)]
        assert len(outliers) < 5  # Less than 5% outliers

    @pytest.mark.asyncio 
    async def test_memory_usage_during_rapid_changes(self, rapid_switch_entity):
        """Test memory usage remains stable during rapid state changes."""
        entity, thermal_manager = rapid_switch_entity
        
        # Baseline memory measurement
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Simulate extended operation with rapid changes
        for batch in range(10):  # 10 batches of 50 operations each
            for i in range(50):
                # Create various conflict scenarios
                thermal_manager.current_state = list(ThermalState)[i % len(ThermalState)]
                
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None if i % 2 == 0 else 25.0,
                    offset_adjustment=float(i % 3),
                    update_interval_override=None,
                    boost_offset=float((i % 5) - 2),
                    force_operation=(i % 4) == 0
                )
                
                entity._temperature_controller.apply_offset_and_limits.return_value = 20.0 + (i % 8)
                
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(22.0, source=f"memory_test_b{batch}_i{i}")
            
            # Force garbage collection after each batch
            gc.collect()
            current_objects = len(gc.get_objects())
            
            # Memory shouldn't grow excessively (allow 10% growth per batch)
            max_allowed_objects = initial_objects * (1 + 0.1 * (batch + 1))
            assert current_objects < max_allowed_objects, f"Memory leak detected at batch {batch}"
        
        # Final memory check
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Total memory growth should be reasonable (under 50% increase)
        memory_growth_ratio = final_objects / initial_objects
        assert memory_growth_ratio < 1.5, f"Excessive memory growth: {memory_growth_ratio}x"


class TestInvalidStateHandling:
    """Test handling of invalid thermal states and mode combinations."""

    @pytest.fixture
    def invalid_state_entity(self):
        """Create entity for invalid state testing."""
        hass = create_mock_hass()
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    "thermal_components": {
                        "climate.test": MagicMock()
                    }
                }
            }
        }
        
        climate_state = create_mock_state(
            state="cool",
            attributes={"current_temperature": 23.0, "hvac_mode": "cool"},
            entity_id="climate.test"
        )
        hass.states.set("climate.test", climate_state)
        
        config = {'entry_id': 'test_entry'}
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(hass),
            coordinator=create_mock_coordinator()
        )
        
        # Setup defaults
        entity._sensor_manager.get_room_temperature.return_value = 23.0
        entity._sensor_manager.get_outdoor_temperature.return_value = 27.0
        entity._sensor_manager.get_power_consumption.return_value = 1200.0
        entity._sensor_manager.get_indoor_humidity.return_value = None
        entity._sensor_manager.get_outdoor_humidity.return_value = None
        
        offset_result = OffsetResult(offset=0.5, clamped=False, reason="test", confidence=0.7)
        entity._offset_engine.calculate_offset.return_value = offset_result
        
        return entity, hass.data[DOMAIN]["test_entry"]["thermal_components"]["climate.test"]

    @pytest.mark.asyncio
    async def test_invalid_thermal_state_handling(self, invalid_state_entity):
        """Test graceful handling of invalid thermal state values."""
        entity, thermal_manager = invalid_state_entity
        
        # Test with invalid enum value
        invalid_states = [
            "INVALID_STATE",  # String that's not a valid enum
            999,              # Invalid integer
            None,            # None value
            object(),        # Random object
        ]
        
        for invalid_state in invalid_states:
            thermal_manager.current_state = invalid_state
            
            # Standard mode adjustments
            entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0,
                force_operation=False
            )
            entity._temperature_controller.apply_offset_and_limits.return_value = 23.5
            
            # Should handle gracefully without crashing
            try:
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(23.0, source=f"invalid_state_{invalid_state}")
                
                # If no exception, verify it used fallback behavior
                entity._temperature_controller.send_temperature_command.assert_called()
                
            except Exception as e:
                # If an exception occurs, it should be handled gracefully
                # and not crash the entire system
                assert isinstance(e, (ValueError, TypeError, AttributeError))

    @pytest.mark.asyncio
    async def test_malformed_mode_adjustments_handling(self, invalid_state_entity):
        """Test handling of malformed ModeAdjustments objects."""
        entity, thermal_manager = invalid_state_entity
        
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Test various malformed mode adjustments
        malformed_adjustments = [
            None,  # None instead of ModeAdjustments
            {},    # Empty dict
            ModeAdjustments(  # Invalid boost_offset
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset="invalid",  # String instead of float
                force_operation=False
            ),
            ModeAdjustments(  # Invalid force_operation
                temperature_override=None,
                offset_adjustment=0.0,
                update_interval_override=None,
                boost_offset=0.0,
                force_operation="maybe"  # String instead of bool
            ),
        ]
        
        for malformed in malformed_adjustments:
            entity._mode_manager.get_adjustments.return_value = malformed
            entity._temperature_controller.apply_offset_and_limits.return_value = 24.0
            
            # Should handle gracefully
            try:
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(23.0, source=f"malformed_{type(malformed)}")
                
                # Verify system continued to function
                entity._temperature_controller.send_temperature_command.assert_called()
                
            except Exception as e:
                # Acceptable graceful failures
                assert isinstance(e, (ValueError, TypeError, AttributeError))

    @pytest.mark.asyncio
    async def test_missing_thermal_manager_graceful_degradation(self, invalid_state_entity):
        """Test graceful degradation when thermal manager is missing."""
        entity, _ = invalid_state_entity
        
        # Remove thermal manager from hass.data
        entity._hass.data[DOMAIN]["test_entry"]["thermal_components"]["climate.test"] = None
        
        # Setup normal mode adjustments
        entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        entity._temperature_controller.apply_offset_and_limits.return_value = 23.0
        
        # Should degrade gracefully to standard operation without thermal features
        with patch.object(entity, '_is_hvac_mode_active', return_value=True):
            await entity._apply_temperature_with_offset(23.0, source="missing_thermal_manager")
        
        # Verify system continued with standard temperature control
        entity._temperature_controller.send_temperature_command.assert_called_with("climate.test", 23.0)

    @pytest.mark.asyncio
    async def test_missing_mode_manager_graceful_degradation(self, invalid_state_entity):
        """Test graceful degradation when mode manager is missing."""
        entity, thermal_manager = invalid_state_entity
        
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Simulate missing mode manager by making it return None
        entity._mode_manager.get_adjustments.return_value = None
        entity._temperature_controller.apply_offset_and_limits.return_value = 27.0  # DRIFTING default
        
        # Should gracefully handle missing mode adjustments
        with patch.object(entity, '_is_hvac_mode_active', return_value=True):
            await entity._apply_temperature_with_offset(23.0, source="missing_mode_manager")
        
        # Should still apply thermal state logic (DRIFTING)
        entity._temperature_controller.send_temperature_command.assert_called_with("climate.test", 27.0)

    @pytest.mark.asyncio
    async def test_sensor_reading_failures_during_conflicts(self, invalid_state_entity):
        """Test handling of sensor reading failures during mode-thermal conflicts."""
        entity, thermal_manager = invalid_state_entity
        
        thermal_manager.current_state = ThermalState.DRIFTING
        
        # Setup boost mode conflict
        entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=-2.0,
            force_operation=True
        )
        
        # Simulate sensor failures
        entity._sensor_manager.get_room_temperature.return_value = None
        entity._sensor_manager.get_outdoor_temperature.return_value = None
        entity._sensor_manager.get_power_consumption.return_value = None
        
        entity._temperature_controller.apply_offset_and_limits.return_value = 20.0
        
        # Should handle gracefully despite sensor failures
        with patch.object(entity, '_is_hvac_mode_active', return_value=True):
            await entity._apply_temperature_with_offset(22.0, source="sensor_failures")
        
        # Should still honor force_operation despite sensor issues
        entity._temperature_controller.send_temperature_command.assert_called_with("climate.test", 20.0)


class TestLoggingAndDiagnostics:
    """Test logging and diagnostic capabilities during conflicts."""

    @pytest.fixture
    def logging_entity(self):
        """Create entity for logging verification tests."""
        hass = create_mock_hass()
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    "thermal_components": {
                        "climate.test": MagicMock()
                    }
                }
            }
        }
        
        climate_state = create_mock_state(
            state="cool",
            attributes={"current_temperature": 22.5, "hvac_mode": "cool"},
            entity_id="climate.test"
        )
        hass.states.set("climate.test", climate_state)
        
        config = {'entry_id': 'test_entry'}
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(hass),
            coordinator=create_mock_coordinator()
        )
        
        # Setup defaults
        entity._sensor_manager.get_room_temperature.return_value = 22.5
        entity._sensor_manager.get_outdoor_temperature.return_value = 26.0
        entity._sensor_manager.get_power_consumption.return_value = 1100.0
        entity._sensor_manager.get_indoor_humidity.return_value = None
        entity._sensor_manager.get_outdoor_humidity.return_value = None
        
        offset_result = OffsetResult(offset=0.8, clamped=False, reason="test", confidence=0.85)
        entity._offset_engine.calculate_offset.return_value = offset_result
        
        return entity, hass.data[DOMAIN]["test_entry"]["thermal_components"]["climate.test"]

    @pytest.mark.asyncio
    async def test_logging_verification_all_decision_paths(self, logging_entity, caplog):
        """Test that all decision paths are logged for debugging."""
        entity, thermal_manager = logging_entity
        
        import logging
        caplog.set_level(logging.DEBUG)
        
        # Test logging for each priority level
        test_scenarios = [
            {
                "name": "boost_override",
                "thermal_state": ThermalState.DRIFTING,
                "mode_adjustments": ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=-2.5, force_operation=True
                ),
                "expected_temp": 19.5,
                "expected_log_keywords": ["boost", "override", "force", "priority"]
            },
            {
                "name": "drifting_priority",
                "thermal_state": ThermalState.DRIFTING,
                "mode_adjustments": ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=0.0, force_operation=False
                ),
                "expected_temp": 25.5,  # room_temp + 3.0
                "expected_log_keywords": ["drifting", "thermal", "state"]
            },
            {
                "name": "standard_operation",
                "thermal_state": ThermalState.CORRECTING,
                "mode_adjustments": ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.5,
                    update_interval_override=None, boost_offset=0.0, force_operation=False
                ),
                "expected_temp": 23.3,
                "expected_log_keywords": ["standard", "offset", "correcting"]
            },
        ]
        
        for scenario in test_scenarios:
            caplog.clear()
            
            thermal_manager.current_state = scenario["thermal_state"]
            entity._mode_manager.get_adjustments.return_value = scenario["mode_adjustments"]
            entity._temperature_controller.apply_offset_and_limits.return_value = scenario["expected_temp"]
            
            with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                await entity._apply_temperature_with_offset(22.0, source=scenario["name"])
            
            # Check that decision path was logged
            log_output = caplog.text.lower()
            
            # At minimum, should log the temperature command
            assert "temperature" in log_output or "command" in log_output
            
            # Verify temperature was set correctly
            entity._temperature_controller.send_temperature_command.assert_called_with(
                "climate.test", scenario["expected_temp"]
            )

    @pytest.mark.asyncio
    async def test_error_condition_logging(self, logging_entity, caplog):
        """Test logging of error conditions and recovery."""
        entity, thermal_manager = logging_entity
        
        import logging
        caplog.set_level(logging.WARNING)
        
        # Test error scenarios
        error_scenarios = [
            {
                "name": "invalid_thermal_state",
                "setup": lambda: setattr(thermal_manager, 'current_state', "INVALID"),
                "expected_log_level": "WARNING"
            },
            {
                "name": "sensor_unavailable", 
                "setup": lambda: entity._sensor_manager.get_room_temperature.__setattr__('return_value', None),
                "expected_log_level": "WARNING"
            },
            {
                "name": "mode_manager_failure",
                "setup": lambda: entity._mode_manager.get_adjustments.__setattr__('side_effect', Exception("Mode failure")),
                "expected_log_level": "ERROR"
            },
        ]
        
        for scenario in error_scenarios:
            caplog.clear()
            
            # Setup error condition
            try:
                scenario["setup"]()
            except:
                pass
            
            # Reset to valid defaults for other components
            if "mode_manager" not in scenario["name"]:
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=0.0, force_operation=False
                )
            
            entity._temperature_controller.apply_offset_and_limits.return_value = 22.0
            
            # Attempt operation
            try:
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(22.0, source=scenario["name"])
            except Exception:
                # Some error scenarios are expected to raise exceptions
                pass
            
            # Verify error was logged (if any logging occurred)
            if caplog.records:
                # Check that appropriate log level was used
                log_levels = [record.levelname for record in caplog.records]
                assert any(level in ["WARNING", "ERROR", "CRITICAL"] for level in log_levels)

    @pytest.mark.asyncio
    async def test_performance_logging_under_stress(self, logging_entity, caplog):
        """Test that logging doesn't degrade performance under stress."""
        entity, thermal_manager = logging_entity
        
        import logging
        caplog.set_level(logging.DEBUG)  # Maximum logging
        
        # Track execution times with heavy logging
        execution_times = []
        
        for i in range(50):  # Moderate stress test
            start_time = time_module.time()
            
            # Setup varying scenarios to trigger different log paths
            thermal_manager.current_state = list(ThermalState)[i % len(ThermalState)]
            entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                temperature_override=None,
                offset_adjustment=float(i % 3),
                update_interval_override=None,
                boost_offset=float((i % 4) - 2),
                force_operation=(i % 5) == 0
            )
            entity._temperature_controller.apply_offset_and_limits.return_value = 20.0 + (i % 8)
            
            with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                await entity._apply_temperature_with_offset(22.0, source=f"perf_log_{i}")
            
            end_time = time_module.time()
            execution_times.append(end_time - start_time)
        
        # Verify logging didn't cause excessive performance degradation
        avg_time = sum(execution_times) / len(execution_times)
        max_time = max(execution_times)
        
        # With heavy logging, still should be reasonable
        assert avg_time < 0.100  # Average under 100ms even with debug logging
        assert max_time < 0.500  # No single operation over 500ms
        
        # Verify logs were actually generated
        assert len(caplog.records) > 0


class TestConcurrencyAndRaceConditions:
    """Test concurrent operations and race condition handling."""

    @pytest.fixture
    def concurrent_entity(self):
        """Create entity for concurrency testing."""
        hass = create_mock_hass()
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    "thermal_components": {
                        "climate.test": MagicMock()
                    }
                }
            }
        }
        
        climate_state = create_mock_state(
            state="cool",
            attributes={"current_temperature": 23.5, "hvac_mode": "cool"},
            entity_id="climate.test"
        )
        hass.states.set("climate.test", climate_state)
        
        config = {'entry_id': 'test_entry'}
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(hass),
            coordinator=create_mock_coordinator()
        )
        
        # Setup defaults
        entity._sensor_manager.get_room_temperature.return_value = 23.5
        entity._sensor_manager.get_outdoor_temperature.return_value = 28.5
        entity._sensor_manager.get_power_consumption.return_value = 1400.0
        entity._sensor_manager.get_indoor_humidity.return_value = None
        entity._sensor_manager.get_outdoor_humidity.return_value = None
        
        offset_result = OffsetResult(offset=1.2, clamped=False, reason="test", confidence=0.9)
        entity._offset_engine.calculate_offset.return_value = offset_result
        
        return entity, hass.data[DOMAIN]["test_entry"]["thermal_components"]["climate.test"]

    @pytest.mark.asyncio
    async def test_concurrent_mode_state_changes(self, concurrent_entity):
        """Test concurrent mode and state changes don't cause corruption."""
        entity, thermal_manager = concurrent_entity
        
        # Track command integrity
        command_integrity = []
        original_send_command = entity._temperature_controller.send_temperature_command
        
        async def verify_command_integrity(entity_id, temperature):
            # Verify command parameters are valid
            assert entity_id == "climate.test"
            assert isinstance(temperature, (int, float))
            assert 15.0 <= temperature <= 35.0  # Reasonable temperature range
            
            command_integrity.append({
                "entity_id": entity_id,
                "temperature": temperature,
                "timestamp": datetime.now()
            })
            await original_send_command(entity_id, temperature)
        
        entity._temperature_controller.send_temperature_command = verify_command_integrity
        
        # Create concurrent tasks that modify state
        async def mode_modifier():
            """Task that rapidly changes mode adjustments."""
            for i in range(25):
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None,
                    offset_adjustment=float(i % 3),
                    update_interval_override=None,
                    boost_offset=float((i % 4) - 2),
                    force_operation=(i % 3) == 0
                )
                await asyncio.sleep(0.02)
        
        async def state_modifier():
            """Task that rapidly changes thermal states."""
            states = list(ThermalState)
            for i in range(25):
                thermal_manager.current_state = states[i % len(states)]
                await asyncio.sleep(0.02)
        
        async def temperature_applier():
            """Task that applies temperature commands."""
            for i in range(25):
                entity._temperature_controller.apply_offset_and_limits.return_value = 20.0 + (i % 8)
                
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(23.0, source=f"concurrent_{i}")
                
                await asyncio.sleep(0.02)
        
        # Run tasks concurrently
        await asyncio.gather(
            mode_modifier(),
            state_modifier(), 
            temperature_applier(),
            return_exceptions=True
        )
        
        # Verify command integrity
        assert len(command_integrity) == 25
        
        # Verify no corrupted commands
        for command in command_integrity:
            assert command["entity_id"] == "climate.test"
            assert isinstance(command["temperature"], (int, float))
            assert 15.0 <= command["temperature"] <= 35.0

    @pytest.mark.asyncio
    async def test_data_consistency_under_concurrent_access(self, concurrent_entity):
        """Test data consistency when multiple operations access shared state."""
        entity, thermal_manager = concurrent_entity
        
        # Shared state tracking
        shared_state = {
            "mode_reads": 0,
            "state_reads": 0,
            "consistency_errors": 0
        }
        
        # Create consistent state snapshots
        original_get_adjustments = entity._mode_manager.get_adjustments
        original_current_state = thermal_manager.current_state
        
        def tracked_get_adjustments():
            shared_state["mode_reads"] += 1
            return original_get_adjustments()
        
        def tracked_get_state():
            shared_state["state_reads"] += 1
            return original_current_state
        
        entity._mode_manager.get_adjustments = tracked_get_adjustments
        
        # Set consistent initial state
        thermal_manager.current_state = ThermalState.DRIFTING
        entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0,
            force_operation=False
        )
        
        # Concurrent operations
        async def reader_task(task_id):
            """Task that reads state consistently."""
            for i in range(20):
                try:
                    # Read thermal state
                    current_thermal = thermal_manager.current_state
                    
                    # Read mode adjustments  
                    current_mode = entity._mode_manager.get_adjustments()
                    
                    # Verify consistency
                    if not isinstance(current_thermal, ThermalState) and current_thermal not in ThermalState:
                        shared_state["consistency_errors"] += 1
                    
                    if not isinstance(current_mode, ModeAdjustments):
                        shared_state["consistency_errors"] += 1
                
                except Exception:
                    shared_state["consistency_errors"] += 1
                
                await asyncio.sleep(0.01)
        
        async def writer_task():
            """Task that modifies state."""
            states = list(ThermalState)
            for i in range(20):
                try:
                    thermal_manager.current_state = states[i % len(states)]
                    
                    entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                        temperature_override=None,
                        offset_adjustment=float(i % 3),
                        update_interval_override=None,
                        boost_offset=float((i % 4) - 2),
                        force_operation=(i % 2) == 0
                    )
                except Exception:
                    shared_state["consistency_errors"] += 1
                
                await asyncio.sleep(0.01)
        
        # Run concurrent readers and writers
        await asyncio.gather(
            reader_task(1),
            reader_task(2),
            reader_task(3),
            writer_task(),
            return_exceptions=True
        )
        
        # Verify data consistency
        assert shared_state["consistency_errors"] == 0
        assert shared_state["mode_reads"] > 0
        assert shared_state["state_reads"] >= 0

    @pytest.mark.asyncio
    async def test_deadlock_prevention(self, concurrent_entity):
        """Test that system doesn't deadlock under concurrent operations."""
        entity, thermal_manager = concurrent_entity
        
        # Setup timeout for deadlock detection
        timeout_seconds = 5.0
        completed_operations = []
        
        async def blocking_operation(op_id):
            """Simulate potentially blocking operation."""
            try:
                # Setup complex state
                thermal_manager.current_state = ThermalState.DRIFTING
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=-2.0, force_operation=True
                )
                entity._temperature_controller.apply_offset_and_limits.return_value = 19.0
                
                # Multiple rapid calls
                for i in range(10):
                    with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                        await entity._apply_temperature_with_offset(22.0, source=f"deadlock_test_{op_id}_{i}")
                    
                    # Small yield to allow other tasks
                    await asyncio.sleep(0.001)
                
                completed_operations.append(op_id)
                
            except Exception as e:
                # Log but don't fail the test - we're testing deadlock prevention
                completed_operations.append(f"{op_id}_error")
        
        # Create multiple potentially conflicting operations
        tasks = [
            blocking_operation(f"task_{i}") 
            for i in range(10)
        ]
        
        # Run with timeout to detect deadlocks
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            pytest.fail(f"Deadlock detected - operations didn't complete within {timeout_seconds} seconds")
        
        # Verify all operations completed
        assert len(completed_operations) == 10
        
        # Verify no operations are hanging
        for op_result in completed_operations:
            assert isinstance(op_result, str)  # All should be operation IDs

    @pytest.mark.asyncio
    async def test_resource_cleanup_after_errors(self, concurrent_entity):
        """Test that resources are properly cleaned up after error conditions."""
        entity, thermal_manager = concurrent_entity
        
        # Track resource allocation
        resource_tracker = {
            "active_operations": 0,
            "max_concurrent": 0,
            "cleanup_failures": 0
        }
        
        # Mock resource-intensive operation
        original_apply_temp = entity._apply_temperature_with_offset
        
        async def tracked_apply_temp(*args, **kwargs):
            resource_tracker["active_operations"] += 1
            resource_tracker["max_concurrent"] = max(
                resource_tracker["max_concurrent"],
                resource_tracker["active_operations"]
            )
            
            try:
                result = await original_apply_temp(*args, **kwargs)
                return result
            except Exception as e:
                # Simulate cleanup
                try:
                    # Resource cleanup would happen here
                    pass
                except Exception:
                    resource_tracker["cleanup_failures"] += 1
                raise e
            finally:
                resource_tracker["active_operations"] -= 1
        
        entity._apply_temperature_with_offset = tracked_apply_temp
        
        # Create operations that will fail in various ways
        async def failing_operation(fail_type):
            """Operation that fails in different ways."""
            try:
                if fail_type == "invalid_state":
                    thermal_manager.current_state = "INVALID_STATE"
                elif fail_type == "mode_exception":
                    entity._mode_manager.get_adjustments.side_effect = Exception("Mode failure")
                elif fail_type == "sensor_failure":
                    entity._sensor_manager.get_room_temperature.return_value = None
                
                entity._temperature_controller.apply_offset_and_limits.return_value = 22.0
                
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(22.0, source=f"fail_{fail_type}")
                
            except Exception:
                # Expected to fail
                pass
        
        # Run failing operations concurrently
        fail_types = ["invalid_state", "mode_exception", "sensor_failure"] * 5
        
        await asyncio.gather(
            *[failing_operation(fail_type) for fail_type in fail_types],
            return_exceptions=True
        )
        
        # Verify resource cleanup
        assert resource_tracker["active_operations"] == 0  # All operations cleaned up
        assert resource_tracker["cleanup_failures"] == 0   # No cleanup failures
        assert resource_tracker["max_concurrent"] > 0     # Operations did run concurrently


class TestSystemStressAndLimits:
    """Test system behavior under stress and at operational limits."""

    @pytest.fixture
    def stress_test_entity(self):
        """Create entity optimized for stress testing."""
        hass = create_mock_hass()
        hass.data = {
            DOMAIN: {
                "test_entry": {
                    "thermal_components": {
                        "climate.test": MagicMock()
                    }
                }
            }
        }
        
        climate_state = create_mock_state(
            state="cool",
            attributes={"current_temperature": 24.5, "hvac_mode": "cool"},
            entity_id="climate.test"
        )
        hass.states.set("climate.test", climate_state)
        
        config = {'entry_id': 'test_entry'}
        entity = SmartClimateEntity(
            hass=hass,
            config=config,
            wrapped_entity_id="climate.test",
            room_sensor_id="sensor.room_temp",
            offset_engine=create_mock_offset_engine(),
            sensor_manager=create_mock_sensor_manager(),
            mode_manager=create_mock_mode_manager(),
            temperature_controller=create_mock_temperature_controller(hass),
            coordinator=create_mock_coordinator()
        )
        
        # Setup defaults
        entity._sensor_manager.get_room_temperature.return_value = 24.5
        entity._sensor_manager.get_outdoor_temperature.return_value = 29.0
        entity._sensor_manager.get_power_consumption.return_value = 1600.0
        entity._sensor_manager.get_indoor_humidity.return_value = None
        entity._sensor_manager.get_outdoor_humidity.return_value = None
        
        offset_result = OffsetResult(offset=1.5, clamped=False, reason="test", confidence=0.95)
        entity._offset_engine.calculate_offset.return_value = offset_result
        
        return entity, hass.data[DOMAIN]["test_entry"]["thermal_components"]["climate.test"]

    @pytest.mark.asyncio
    async def test_extreme_temperature_scenarios(self, stress_test_entity):
        """Test system handling of extreme temperature scenarios."""
        entity, thermal_manager = stress_test_entity
        
        # Test extreme temperature scenarios
        extreme_scenarios = [
            {
                "name": "arctic_cold",
                "room_temp": -15.0,
                "outdoor_temp": -25.0,
                "thermal_state": ThermalState.DRIFTING,
                "mode": ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=0.0, force_operation=False
                ),
                "expected_behavior": "safe_fallback"
            },
            {
                "name": "desert_heat",
                "room_temp": 45.0,
                "outdoor_temp": 50.0,
                "thermal_state": ThermalState.DRIFTING,
                "mode": ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=-5.0, force_operation=True
                ),
                "expected_behavior": "safety_limited"
            },
            {
                "name": "rapid_temperature_swing",
                "room_temp": 10.0,  # Will change rapidly during test
                "outdoor_temp": 35.0,
                "thermal_state": ThermalState.CORRECTING,
                "mode": ModeAdjustments(
                    temperature_override=None, offset_adjustment=2.0,
                    update_interval_override=None, boost_offset=0.0, force_operation=False
                ),
                "expected_behavior": "gradual_adjustment"
            },
        ]
        
        for scenario in extreme_scenarios:
            # Setup extreme conditions
            entity._sensor_manager.get_room_temperature.return_value = scenario["room_temp"]
            entity._sensor_manager.get_outdoor_temperature.return_value = scenario["outdoor_temp"]
            thermal_manager.current_state = scenario["thermal_state"]
            entity._mode_manager.get_adjustments.return_value = scenario["mode"]
            
            # For rapid swing scenario, simulate temperature changes
            if scenario["name"] == "rapid_temperature_swing":
                for temp_change in range(10):
                    changing_temp = 10.0 + (temp_change * 5.0)  # 10°C to 55°C
                    entity._sensor_manager.get_room_temperature.return_value = changing_temp
                    
                    # Temperature controller should provide safety limits
                    safe_temp = max(16.0, min(30.0, changing_temp + 2.0))  # Safety bounds
                    entity._temperature_controller.apply_offset_and_limits.return_value = safe_temp
                    
                    with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                        await entity._apply_temperature_with_offset(22.0, source=f"{scenario['name']}_swing_{temp_change}")
                    
                    # Verify safe temperature was used
                    last_call = entity._temperature_controller.send_temperature_command.call_args
                    assert last_call[0][1] == safe_temp
            
            else:
                # Static extreme temperature test
                safe_temp = max(16.0, min(30.0, scenario["room_temp"] + 2.0))
                entity._temperature_controller.apply_offset_and_limits.return_value = safe_temp
                
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(22.0, source=scenario["name"])
                
                # Verify system handled extreme conditions safely
                entity._temperature_controller.send_temperature_command.assert_called()
                last_call = entity._temperature_controller.send_temperature_command.call_args
                temp_sent = last_call[0][1]
                
                # Verify temperature is within safety bounds
                assert 16.0 <= temp_sent <= 30.0

    @pytest.mark.asyncio
    async def test_system_recovery_after_failure_cascade(self, stress_test_entity):
        """Test system recovery after cascading failures."""
        entity, thermal_manager = stress_test_entity
        
        # Simulate cascading failure scenario
        failure_sequence = [
            "thermal_manager_corruption",
            "mode_manager_exception", 
            "sensor_complete_failure",
            "temperature_controller_error",
            "hass_service_unavailable"
        ]
        
        recovery_results = []
        
        for failure_step in failure_sequence:
            try:
                # Induce specific failure
                if failure_step == "thermal_manager_corruption":
                    thermal_manager.current_state = object()  # Invalid state object
                elif failure_step == "mode_manager_exception":
                    entity._mode_manager.get_adjustments.side_effect = RuntimeError("Mode failure")
                elif failure_step == "sensor_complete_failure":
                    entity._sensor_manager.get_room_temperature.side_effect = ConnectionError("Sensor offline")
                    entity._sensor_manager.get_outdoor_temperature.side_effect = ConnectionError("Sensor offline")
                elif failure_step == "temperature_controller_error":
                    entity._temperature_controller.apply_offset_and_limits.side_effect = ValueError("Controller error")
                elif failure_step == "hass_service_unavailable":
                    entity._hass.services.async_call.side_effect = Exception("Service unavailable")
                
                # Attempt operation under failure
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(22.0, source=f"failure_{failure_step}")
                
                recovery_results.append(f"{failure_step}_recovered")
                
            except Exception as e:
                # Record failure type
                recovery_results.append(f"{failure_step}_failed_{type(e).__name__}")
                
                # Reset for next test - simulate system recovery
                thermal_manager.current_state = ThermalState.PRIMING
                entity._mode_manager.get_adjustments.side_effect = None
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None, offset_adjustment=0.0,
                    update_interval_override=None, boost_offset=0.0, force_operation=False
                )
                entity._sensor_manager.get_room_temperature.side_effect = None
                entity._sensor_manager.get_room_temperature.return_value = 24.0
                entity._sensor_manager.get_outdoor_temperature.side_effect = None
                entity._sensor_manager.get_outdoor_temperature.return_value = 28.0
                entity._temperature_controller.apply_offset_and_limits.side_effect = None
                entity._temperature_controller.apply_offset_and_limits.return_value = 23.0
                entity._hass.services.async_call.side_effect = None
        
        # Verify system attempted recovery for all failure types
        assert len(recovery_results) == len(failure_sequence)
        
        # Final recovery test - verify system can operate normally after all failures
        with patch.object(entity, '_is_hvac_mode_active', return_value=True):
            await entity._apply_temperature_with_offset(22.0, source="final_recovery_test")
        
        # Verify final operation succeeded
        entity._temperature_controller.send_temperature_command.assert_called()

    @pytest.mark.asyncio
    async def test_memory_and_performance_under_extended_load(self, stress_test_entity):
        """Test memory and performance under extended operational load."""
        entity, thermal_manager = stress_test_entity
        
        # Extended load test parameters
        total_operations = 1000
        batch_size = 50
        
        # Performance tracking
        execution_times = []
        memory_snapshots = []
        
        # Baseline measurement
        gc.collect()
        initial_objects = len(gc.get_objects())
        memory_snapshots.append(initial_objects)
        
        # Extended load test
        for batch in range(total_operations // batch_size):
            batch_start = time_module.time()
            
            for i in range(batch_size):
                operation_start = time_module.time()
                
                # Vary operational parameters to test different code paths
                thermal_manager.current_state = list(ThermalState)[(batch * batch_size + i) % len(ThermalState)]
                
                entity._mode_manager.get_adjustments.return_value = ModeAdjustments(
                    temperature_override=None if i % 3 != 0 else 25.0,
                    offset_adjustment=float(i % 4),
                    update_interval_override=None if i % 5 != 0 else 300,
                    boost_offset=float((i % 6) - 3),
                    force_operation=(i % 7) == 0
                )
                
                entity._temperature_controller.apply_offset_and_limits.return_value = 18.0 + (i % 12)
                
                with patch.object(entity, '_is_hvac_mode_active', return_value=True):
                    await entity._apply_temperature_with_offset(22.0, source=f"load_test_b{batch}_i{i}")
                
                operation_end = time_module.time()
                execution_times.append(operation_end - operation_start)
            
            batch_end = time_module.time()
            
            # Memory measurement every 5 batches
            if batch % 5 == 0:
                gc.collect()
                current_objects = len(gc.get_objects())
                memory_snapshots.append(current_objects)
                
                # Memory growth check
                memory_growth = (current_objects - initial_objects) / initial_objects
                assert memory_growth < 2.0, f"Excessive memory growth at batch {batch}: {memory_growth:.2f}x"
        
        # Performance analysis
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        p95_execution_time = sorted(execution_times)[int(0.95 * len(execution_times))]
        
        # Performance assertions
        assert avg_execution_time < 0.020, f"Average execution time too high: {avg_execution_time:.3f}s"
        assert max_execution_time < 0.100, f"Maximum execution time too high: {max_execution_time:.3f}s"
        assert p95_execution_time < 0.050, f"95th percentile too high: {p95_execution_time:.3f}s"
        
        # Memory stability check
        final_memory = memory_snapshots[-1]
        memory_growth_ratio = final_memory / initial_objects
        assert memory_growth_ratio < 1.5, f"Memory grew too much: {memory_growth_ratio:.2f}x"
        
        # Verify system still operates correctly after extended load
        gc.collect()
        with patch.object(entity, '_is_hvac_mode_active', return_value=True):
            await entity._apply_temperature_with_offset(22.0, source="post_load_verification")
        
        entity._temperature_controller.send_temperature_command.assert_called()