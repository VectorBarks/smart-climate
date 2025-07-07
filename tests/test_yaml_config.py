"""ABOUTME: Test suite for YAML configuration validation.
Tests all aspects of YAML config parsing, validation, and error handling."""

import pytest
from unittest.mock import Mock, patch
import voluptuous as vol

from custom_components.smart_climate.config_schema import CONFIG_SCHEMA
from custom_components.smart_climate.const import (
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTDOOR_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_OFFSET,
    CONF_MIN_TEMPERATURE,
    CONF_MAX_TEMPERATURE,
    CONF_UPDATE_INTERVAL,
    CONF_ML_ENABLED,
    DEFAULT_MAX_OFFSET,
    DEFAULT_MIN_TEMPERATURE,
    DEFAULT_MAX_TEMPERATURE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_ML_ENABLED,
)


class TestYAMLConfigValidation:
    """Test YAML configuration validation."""

    def test_valid_minimal_config(self):
        """Test valid minimal configuration with only required fields."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
        }
        
        result = CONFIG_SCHEMA(config)
        
        # Required fields should be present
        assert result[CONF_CLIMATE_ENTITY] == "climate.living_room"
        assert result[CONF_ROOM_SENSOR] == "sensor.living_room_temperature"
        
        # Optional fields should have defaults
        assert result[CONF_MAX_OFFSET] == DEFAULT_MAX_OFFSET
        assert result[CONF_MIN_TEMPERATURE] == DEFAULT_MIN_TEMPERATURE
        assert result[CONF_MAX_TEMPERATURE] == DEFAULT_MAX_TEMPERATURE
        assert result[CONF_UPDATE_INTERVAL] == DEFAULT_UPDATE_INTERVAL
        assert result[CONF_ML_ENABLED] == DEFAULT_ML_ENABLED

    def test_valid_full_config(self):
        """Test valid configuration with all fields specified."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_OUTDOOR_SENSOR: "sensor.outdoor_temperature",
            CONF_POWER_SENSOR: "sensor.ac_power",
            CONF_MAX_OFFSET: 3.0,
            CONF_MIN_TEMPERATURE: 18.0,
            CONF_MAX_TEMPERATURE: 28.0,
            CONF_UPDATE_INTERVAL: 300,
            CONF_ML_ENABLED: False,
        }
        
        result = CONFIG_SCHEMA(config)
        
        # All values should be preserved
        assert result[CONF_CLIMATE_ENTITY] == "climate.living_room"
        assert result[CONF_ROOM_SENSOR] == "sensor.living_room_temperature"
        assert result[CONF_OUTDOOR_SENSOR] == "sensor.outdoor_temperature"
        assert result[CONF_POWER_SENSOR] == "sensor.ac_power"
        assert result[CONF_MAX_OFFSET] == 3.0
        assert result[CONF_MIN_TEMPERATURE] == 18.0
        assert result[CONF_MAX_TEMPERATURE] == 28.0
        assert result[CONF_UPDATE_INTERVAL] == 300
        assert result[CONF_ML_ENABLED] == False

    def test_type_coercion(self):
        """Test that numeric values are properly coerced."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MAX_OFFSET: "4.5",  # String should be converted to float
            CONF_MIN_TEMPERATURE: "17",  # String should be converted to float
            CONF_MAX_TEMPERATURE: "29",  # String should be converted to float
            CONF_UPDATE_INTERVAL: "240",  # String should be converted to int
            CONF_ML_ENABLED: "true",  # String should be converted to bool
        }
        
        result = CONFIG_SCHEMA(config)
        
        assert result[CONF_MAX_OFFSET] == 4.5
        assert result[CONF_MIN_TEMPERATURE] == 17.0
        assert result[CONF_MAX_TEMPERATURE] == 29.0
        assert result[CONF_UPDATE_INTERVAL] == 240
        assert result[CONF_ML_ENABLED] == True

    def test_boolean_variations(self):
        """Test different boolean value formats."""
        test_cases = [
            ("true", True),
            ("false", False),
            ("True", True),
            ("False", False),
            ("yes", True),
            ("no", False),
            ("1", True),
            ("0", False),
            (True, True),
            (False, False),
        ]
        
        for input_value, expected in test_cases:
            config = {
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.living_room_temperature",
                CONF_ML_ENABLED: input_value,
            }
            
            result = CONFIG_SCHEMA(config)
            assert result[CONF_ML_ENABLED] == expected

    def test_missing_required_climate_entity(self):
        """Test error when climate_entity is missing."""
        config = {
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "required key not provided" in str(excinfo.value)

    def test_missing_required_room_sensor(self):
        """Test error when room_sensor is missing."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "required key not provided" in str(excinfo.value)

    def test_invalid_entity_id_format(self):
        """Test error for invalid entity ID format."""
        config = {
            CONF_CLIMATE_ENTITY: "invalid_entity_id",  # No domain.entity format
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "entity ID is invalid" in str(excinfo.value)

    def test_temperature_limits_validation(self):
        """Test temperature limits validation."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MIN_TEMPERATURE: 25.0,
            CONF_MAX_TEMPERATURE: 20.0,  # Max less than min
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "min_temperature (25.0) must be less than max_temperature (20.0)" in str(excinfo.value)

    def test_equal_temperature_limits_validation(self):
        """Test validation fails when temperature limits are equal."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MIN_TEMPERATURE: 20.0,
            CONF_MAX_TEMPERATURE: 20.0,  # Max equal to min
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "min_temperature (20.0) must be less than max_temperature (20.0)" in str(excinfo.value)

    def test_zero_max_offset_validation(self):
        """Test validation fails when max_offset is zero."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MAX_OFFSET: 0.0,
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "max_offset (0.0) must be greater than 0" in str(excinfo.value)

    def test_negative_max_offset_validation(self):
        """Test validation fails when max_offset is negative."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MAX_OFFSET: -2.0,
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "max_offset (-2.0) must be greater than 0" in str(excinfo.value)

    def test_invalid_update_interval(self):
        """Test error for invalid update interval."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_UPDATE_INTERVAL: "invalid",  # Non-numeric string
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        assert "invalid literal for int()" in str(excinfo.value)

    def test_edge_case_values(self):
        """Test edge case values that should be valid."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MAX_OFFSET: 0.1,  # Very small but positive
            CONF_MIN_TEMPERATURE: -10.0,  # Very low temperature
            CONF_MAX_TEMPERATURE: 50.0,  # Very high temperature
            CONF_UPDATE_INTERVAL: 30,  # Very frequent updates
        }
        
        result = CONFIG_SCHEMA(config)
        
        assert result[CONF_MAX_OFFSET] == 0.1
        assert result[CONF_MIN_TEMPERATURE] == -10.0
        assert result[CONF_MAX_TEMPERATURE] == 50.0
        assert result[CONF_UPDATE_INTERVAL] == 30

    def test_extra_fields_allowed(self):
        """Test that extra fields are allowed (for future compatibility)."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            "future_field": "future_value",
            "another_field": 42,
        }
        
        result = CONFIG_SCHEMA(config)
        
        # Required fields should be present
        assert result[CONF_CLIMATE_ENTITY] == "climate.living_room"
        assert result[CONF_ROOM_SENSOR] == "sensor.living_room_temperature"
        
        # Extra fields should be preserved
        assert result["future_field"] == "future_value"
        assert result["another_field"] == 42


class TestMultipleInstancesSupport:
    """Test support for multiple smart climate instances."""

    def test_multiple_valid_configs(self):
        """Test that multiple valid configurations can be processed."""
        configs = [
            {
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            },
            {
                CONF_CLIMATE_ENTITY: "climate.bedroom",
                CONF_ROOM_SENSOR: "sensor.bedroom_temperature",
                CONF_OUTDOOR_SENSOR: "sensor.outdoor_temperature",
            },
            {
                CONF_CLIMATE_ENTITY: "climate.office",
                CONF_ROOM_SENSOR: "sensor.office_temperature",
                CONF_POWER_SENSOR: "sensor.office_ac_power",
                CONF_MAX_OFFSET: 2.0,
                CONF_ML_ENABLED: False,
            },
        ]
        
        results = []
        for config in configs:
            result = CONFIG_SCHEMA(config)
            results.append(result)
        
        # All configurations should be valid
        assert len(results) == 3
        
        # Check first config
        assert results[0][CONF_CLIMATE_ENTITY] == "climate.living_room"
        assert results[0][CONF_ROOM_SENSOR] == "sensor.living_room_temperature"
        assert results[0][CONF_MAX_OFFSET] == DEFAULT_MAX_OFFSET
        
        # Check second config
        assert results[1][CONF_CLIMATE_ENTITY] == "climate.bedroom"
        assert results[1][CONF_ROOM_SENSOR] == "sensor.bedroom_temperature"
        assert results[1][CONF_OUTDOOR_SENSOR] == "sensor.outdoor_temperature"
        
        # Check third config
        assert results[2][CONF_CLIMATE_ENTITY] == "climate.office"
        assert results[2][CONF_ROOM_SENSOR] == "sensor.office_temperature"
        assert results[2][CONF_POWER_SENSOR] == "sensor.office_ac_power"
        assert results[2][CONF_MAX_OFFSET] == 2.0
        assert results[2][CONF_ML_ENABLED] == False

    def test_mixed_valid_invalid_configs(self):
        """Test that validation works correctly for mixed configurations."""
        configs = [
            {
                CONF_CLIMATE_ENTITY: "climate.living_room",
                CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            },
            {
                CONF_CLIMATE_ENTITY: "climate.bedroom",
                # Missing room_sensor - should fail
            },
            {
                CONF_CLIMATE_ENTITY: "climate.office",
                CONF_ROOM_SENSOR: "sensor.office_temperature",
                CONF_MAX_OFFSET: 3.0,
            },
        ]
        
        # First config should validate
        result1 = CONFIG_SCHEMA(configs[0])
        assert result1[CONF_CLIMATE_ENTITY] == "climate.living_room"
        
        # Second config should fail validation
        with pytest.raises(vol.Invalid):
            CONFIG_SCHEMA(configs[1])
        
        # Third config should validate
        result3 = CONFIG_SCHEMA(configs[2])
        assert result3[CONF_CLIMATE_ENTITY] == "climate.office"
        assert result3[CONF_MAX_OFFSET] == 3.0


class TestConfigSchemaErrorMessages:
    """Test that configuration error messages are clear and helpful."""

    def test_clear_error_for_missing_required_fields(self):
        """Test that error messages clearly indicate missing required fields."""
        config = {}
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        error_msg = str(excinfo.value)
        assert "required key not provided" in error_msg

    def test_clear_error_for_invalid_entity_ids(self):
        """Test that error messages clearly indicate invalid entity IDs."""
        config = {
            CONF_CLIMATE_ENTITY: "not_valid",
            CONF_ROOM_SENSOR: "sensor.valid",
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        error_msg = str(excinfo.value)
        assert "entity ID is invalid" in error_msg

    def test_clear_error_for_temperature_limits(self):
        """Test that temperature limit errors are clear."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MIN_TEMPERATURE: 30.0,
            CONF_MAX_TEMPERATURE: 20.0,
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        error_msg = str(excinfo.value)
        assert "min_temperature (30.0) must be less than max_temperature (20.0)" in error_msg

    def test_clear_error_for_offset_limits(self):
        """Test that offset limit errors are clear."""
        config = {
            CONF_CLIMATE_ENTITY: "climate.living_room",
            CONF_ROOM_SENSOR: "sensor.living_room_temperature",
            CONF_MAX_OFFSET: -1.0,
        }
        
        with pytest.raises(vol.Invalid) as excinfo:
            CONFIG_SCHEMA(config)
        
        error_msg = str(excinfo.value)
        assert "max_offset (-1.0) must be greater than 0" in error_msg