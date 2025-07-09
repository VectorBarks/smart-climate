"""Integration tests for the Smart Climate dashboard feature."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
import yaml
from datetime import datetime, timedelta
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.const import STATE_ON, STATE_OFF, PERCENTAGE
from custom_components.smart_climate.const import DOMAIN, PLATFORMS


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry for integration tests."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_integration_entry"
    entry.unique_id = "integration_unique_id"
    entry.title = "Integration Test Climate"
    entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.test_room",
        "power_sensor": "sensor.test_power",
        "outdoor_sensor": "sensor.test_outdoor",
        "max_offset": 5.0,
        "enable_learning": True,
        "update_interval": 180,
        "gradual_adjustment_rate": 0.5,
    }
    return entry


@pytest.fixture
def mock_hass():
    """Create a comprehensive mock HomeAssistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.states = Mock()
    hass.services = Mock()
    hass.config_entries = Mock()
    hass.helpers = Mock()
    
    # Mock persistent notification service
    hass.services.async_call = AsyncMock()
    
    # Mock state getter
    def mock_get_state(entity_id):
        states = {
            "climate.test_ac": Mock(
                state="cool",
                attributes={
                    "temperature": 24.0,
                    "current_temperature": 25.0,
                    "hvac_modes": ["off", "cool", "heat", "auto"],
                }
            ),
            "sensor.test_room": Mock(state="23.5", attributes={}),
            "sensor.test_power": Mock(state="850", attributes={}),
            "sensor.test_outdoor": Mock(state="30.0", attributes={}),
        }
        return states.get(entity_id)
    
    hass.states.get = mock_get_state
    
    return hass


class TestDashboardIntegrationSetup:
    """Test the complete dashboard integration setup flow."""
    
    async def test_setup_creates_all_dashboard_sensors(self, mock_hass, mock_config_entry):
        """Test that integration setup creates all 5 dashboard sensors."""
        from custom_components.smart_climate import async_setup_entry
        from custom_components.smart_climate.sensor import async_setup_entry as sensor_setup
        
        # Mock the platform setup
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        # Setup the integration
        result = await async_setup_entry(mock_hass, mock_config_entry)
        assert result is True
        
        # Verify sensor platform is included
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()
        platforms = mock_hass.config_entries.async_forward_entry_setups.call_args[0][1]
        assert "sensor" in platforms
        
        # Now test sensor setup directly
        async_add_entities = AsyncMock()
        await sensor_setup(mock_hass, mock_config_entry, async_add_entities)
        
        # Should create 5 sensors
        async_add_entities.assert_called_once()
        sensors = async_add_entities.call_args[0][0]
        assert len(sensors) == 5
        
        # Verify sensor types
        sensor_types = {s._sensor_type for s in sensors}
        expected_types = {
            "offset_current",
            "learning_progress",
            "accuracy_current", 
            "calibration_status",
            "hysteresis_state"
        }
        assert sensor_types == expected_types
    
    async def test_sensors_update_from_coordinator(self, mock_hass, mock_config_entry):
        """Test that sensor values update when coordinator data changes."""
        from custom_components.smart_climate.sensor import (
            OffsetCurrentSensor,
            LearningProgressSensor,
            AccuracyCurrentSensor,
        )
        from custom_components.smart_climate.offset_engine import OffsetEngine
        
        # Create a real offset engine with mock coordinator
        offset_engine = OffsetEngine(mock_config_entry.data)
        mock_coordinator = Mock()
        mock_coordinator.data = Mock(calculated_offset=2.5)
        offset_engine._coordinator = mock_coordinator
        
        # Create sensors
        offset_sensor = OffsetCurrentSensor(offset_engine, "climate.test_ac", mock_config_entry)
        progress_sensor = LearningProgressSensor(offset_engine, "climate.test_ac", mock_config_entry)
        accuracy_sensor = AccuracyCurrentSensor(offset_engine, "climate.test_ac", mock_config_entry)
        
        # Initial values
        assert offset_sensor.native_value == 2.5
        assert progress_sensor.native_value == 0  # No samples yet
        assert accuracy_sensor.native_value == 0  # No accuracy yet
        
        # Update coordinator data
        mock_coordinator.data.calculated_offset = 3.0
        offset_engine.get_learning_info = Mock(return_value={
            "enabled": True,
            "samples": 15,
            "accuracy": 0.85,
        })
        
        # Values should update
        assert offset_sensor.native_value == 3.0
        assert progress_sensor.native_value == 100  # 15 samples = 100% (capped)
        assert accuracy_sensor.native_value == 85  # 0.85 * 100


class TestDashboardServiceIntegration:
    """Test the dashboard generation service integration."""
    
    async def test_service_registration(self, mock_hass, mock_config_entry):
        """Test that the generate_dashboard service is registered."""
        from custom_components.smart_climate import async_setup_entry
        
        # Setup the integration
        await async_setup_entry(mock_hass, mock_config_entry)
        
        # Check service is registered
        # This will fail until service is implemented
        assert mock_hass.services.async_register.called
        service_calls = [call for call in mock_hass.services.async_register.call_args_list
                        if call[0][1] == "generate_dashboard"]
        assert len(service_calls) == 1
    
    async def test_dashboard_generation_valid_entity(self, mock_hass, mock_config_entry):
        """Test dashboard generation with valid entity."""
        # This test will be enabled once service is implemented
        pass
    
    async def test_dashboard_generation_invalid_entity(self, mock_hass, mock_config_entry):
        """Test dashboard generation with invalid entity."""
        # This test will be enabled once service is implemented
        pass
    
    async def test_notification_content_valid_yaml(self, mock_hass, mock_config_entry):
        """Test that generated dashboard YAML is valid."""
        # This test will be enabled once service is implemented
        pass


class TestMultipleClimateInstances:
    """Test dashboard integration with multiple Smart Climate instances."""
    
    async def test_multiple_instances_create_separate_sensors(self, mock_hass):
        """Test that multiple climate instances create separate sensor sets."""
        from custom_components.smart_climate import async_setup_entry
        from custom_components.smart_climate.sensor import async_setup_entry as sensor_setup
        
        # Create two config entries
        entry1 = Mock(spec=ConfigEntry)
        entry1.entry_id = "entry1"
        entry1.unique_id = "unique1"
        entry1.title = "Living Room"
        entry1.data = {
            "climate_entity": "climate.living_room",
            "room_sensor": "sensor.living_room_temp",
        }
        
        entry2 = Mock(spec=ConfigEntry)
        entry2.entry_id = "entry2"
        entry2.unique_id = "unique2"
        entry2.title = "Bedroom"
        entry2.data = {
            "climate_entity": "climate.bedroom",
            "room_sensor": "sensor.bedroom_temp",
        }
        
        # Mock platform setup
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        # Setup both entries
        await async_setup_entry(mock_hass, entry1)
        await async_setup_entry(mock_hass, entry2)
        
        # Test sensor creation for both
        async_add_entities1 = AsyncMock()
        async_add_entities2 = AsyncMock()
        
        await sensor_setup(mock_hass, entry1, async_add_entities1)
        await sensor_setup(mock_hass, entry2, async_add_entities2)
        
        # Each should create 5 sensors
        sensors1 = async_add_entities1.call_args[0][0]
        sensors2 = async_add_entities2.call_args[0][0]
        
        assert len(sensors1) == 5
        assert len(sensors2) == 5
        
        # Verify unique IDs are different
        unique_ids1 = {s.unique_id for s in sensors1}
        unique_ids2 = {s.unique_id for s in sensors2}
        assert len(unique_ids1.intersection(unique_ids2)) == 0


class TestMissingOptionalEntities:
    """Test dashboard integration when optional entities are missing."""
    
    async def test_sensors_work_without_power_sensor(self, mock_hass):
        """Test that dashboard sensors work when power sensor is missing."""
        from custom_components.smart_climate.sensor import HysteresisStateSensor
        from custom_components.smart_climate.offset_engine import OffsetEngine
        
        # Config without power sensor
        config_entry = Mock(spec=ConfigEntry)
        config_entry.unique_id = "no_power"
        config_entry.title = "No Power Test"
        config_entry.data = {
            "climate_entity": "climate.test",
            "room_sensor": "sensor.room",
            # No power_sensor
        }
        
        # Create offset engine
        offset_engine = OffsetEngine(config_entry.data)
        offset_engine.get_learning_info = Mock(return_value={
            "hysteresis_enabled": False,
            "hysteresis_state": "no_power_sensor",
        })
        
        # Create hysteresis sensor
        sensor = HysteresisStateSensor(offset_engine, "climate.test", config_entry)
        
        # Should show appropriate state
        assert sensor.native_value == "No power sensor"
        
        # Attributes should indicate no power sensor
        attrs = sensor.extra_state_attributes
        assert attrs["power_sensor_configured"] is False
        assert attrs["start_threshold"] == "Not available"
        assert attrs["stop_threshold"] == "Not available"


class TestDashboardPerformance:
    """Test dashboard performance characteristics."""
    
    async def test_sensor_update_performance(self, mock_hass, mock_config_entry):
        """Test that sensor updates don't slow down HA."""
        from custom_components.smart_climate.sensor import async_setup_entry
        import time
        
        # Setup sensors
        async_add_entities = AsyncMock()
        
        start_time = time.time()
        await async_setup_entry(mock_hass, mock_config_entry, async_add_entities)
        setup_time = time.time() - start_time
        
        # Setup should be fast (< 100ms)
        assert setup_time < 0.1
        
        # Get sensors
        sensors = async_add_entities.call_args[0][0]
        
        # Test update performance
        for sensor in sensors:
            start_time = time.time()
            _ = sensor.native_value
            _ = sensor.extra_state_attributes if hasattr(sensor, 'extra_state_attributes') else {}
            update_time = time.time() - start_time
            
            # Each sensor update should be fast (< 10ms)
            assert update_time < 0.01
    
    async def test_multiple_instance_scalability(self, mock_hass):
        """Test performance with many climate instances."""
        from custom_components.smart_climate import async_setup_entry
        import time
        
        # Create 10 config entries
        entries = []
        for i in range(10):
            entry = Mock(spec=ConfigEntry)
            entry.entry_id = f"entry_{i}"
            entry.unique_id = f"unique_{i}"
            entry.title = f"Climate {i}"
            entry.data = {
                "climate_entity": f"climate.zone_{i}",
                "room_sensor": f"sensor.room_{i}",
            }
            entries.append(entry)
        
        # Mock platform setup
        mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
        
        # Setup all entries and measure time
        start_time = time.time()
        for entry in entries:
            await async_setup_entry(mock_hass, entry)
        total_time = time.time() - start_time
        
        # Should handle 10 instances in reasonable time (< 1 second)
        assert total_time < 1.0


class TestDashboardErrorScenarios:
    """Test dashboard error handling scenarios."""
    
    async def test_coordinator_unavailable(self, mock_hass, mock_config_entry):
        """Test sensor behavior when coordinator is unavailable."""
        from custom_components.smart_climate.sensor import OffsetCurrentSensor
        from custom_components.smart_climate.offset_engine import OffsetEngine
        
        # Create offset engine without coordinator
        offset_engine = OffsetEngine(mock_config_entry.data)
        # No coordinator set
        
        sensor = OffsetCurrentSensor(offset_engine, "climate.test", mock_config_entry)
        
        # Should not be available
        assert sensor.available is False
        assert sensor.native_value is None
    
    async def test_learning_info_exception_handling(self, mock_hass, mock_config_entry):
        """Test sensors handle exceptions gracefully."""
        from custom_components.smart_climate.sensor import (
            LearningProgressSensor,
            CalibrationStatusSensor,
        )
        from custom_components.smart_climate.offset_engine import OffsetEngine
        
        # Create offset engine that throws exception
        offset_engine = OffsetEngine(mock_config_entry.data)
        offset_engine.get_learning_info = Mock(side_effect=Exception("Test error"))
        
        # Create sensors
        progress_sensor = LearningProgressSensor(offset_engine, "climate.test", mock_config_entry)
        calibration_sensor = CalibrationStatusSensor(offset_engine, "climate.test", mock_config_entry)
        
        # Should return safe defaults
        assert progress_sensor.native_value == 0
        assert calibration_sensor.native_value == "Unknown"
        
        # Attributes should also handle errors
        attrs = calibration_sensor.extra_state_attributes
        assert attrs["samples_collected"] == 0
        assert attrs["learning_enabled"] is False


class TestDashboardYAMLValidity:
    """Test the dashboard YAML template validity."""
    
    async def test_dashboard_template_is_valid_yaml(self):
        """Test that the dashboard template is valid YAML."""
        import os
        
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "custom_components/smart_climate/dashboard/dashboard.yaml"
        )
        
        # Read and parse the template
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Should parse without errors
        parsed = yaml.safe_load(content)
        assert parsed is not None
        assert "title" in parsed
        assert "views" in parsed
        
        # Should have placeholders
        assert "REPLACE_ME_NAME" in content
        assert "REPLACE_ME_ENTITY" in content
    
    async def test_dashboard_template_structure(self):
        """Test that dashboard template has expected structure."""
        import os
        
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "custom_components/smart_climate/dashboard/dashboard.yaml"
        )
        
        with open(template_path, 'r') as f:
            parsed = yaml.safe_load(f.read())
        
        # Check structure
        assert len(parsed["views"]) >= 1
        
        # Check first view has expected cards
        overview = parsed["views"][0]
        assert overview["title"] == "Overview"
        assert "cards" in overview
        
        # Should have climate control, gauges, status entities
        card_types = []
        for card in overview["cards"]:
            if "type" in card:
                card_types.append(card["type"])
            # Handle nested cards
            if "cards" in card:
                for nested in card["cards"]:
                    if "type" in nested:
                        card_types.append(nested["type"])
        
        # Should have key card types
        assert "thermostat" in card_types
        assert "gauge" in card_types
        assert "entities" in card_types
        assert "history-graph" in card_types