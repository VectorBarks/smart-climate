"""ABOUTME: Tests for configurable gradual adjustment rate feature.
Tests config flow validation, temperature controller initialization, and adjustment behavior."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME

from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_GRADUAL_ADJUSTMENT_RATE,
    DEFAULT_GRADUAL_ADJUSTMENT_RATE,
)
from custom_components.smart_climate.config_flow import SmartClimateConfigFlow
from custom_components.smart_climate.temperature_controller import (
    TemperatureController,
    TemperatureLimits,
)
from custom_components.smart_climate.models import ModeAdjustments


class TestGradualAdjustmentRateConfigFlow:
    """Test gradual adjustment rate in config flow."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.data = {}
        hass.config_entries = Mock(spec=config_entries.ConfigEntries)
        hass.config_entries.async_entries.return_value = []
        
        # Mock states for entity selection
        states = []
        
        # Add climate entity
        climate = Mock()
        climate.entity_id = "climate.test"
        climate.attributes = {"friendly_name": "Test Climate"}
        states.append(climate)
        
        # Add temperature sensor
        sensor = Mock()
        sensor.entity_id = "sensor.test_temp"
        sensor.attributes = {"friendly_name": "Test Temperature", "device_class": "temperature"}
        states.append(sensor)
        
        hass.states = Mock()
        hass.states.async_all.return_value = states
        hass.states.get.side_effect = lambda entity_id: next(
            (state for state in states if state.entity_id == entity_id), None
        )
        
        return hass
    
    async def test_config_flow_gradual_adjustment_rate_field(self, mock_hass):
        """Test gradual adjustment rate field exists in config flow."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        result = await flow.async_step_user()
        
        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["step_id"] == "user"
        
        # Check that gradual adjustment rate field is in the schema
        schema_keys = list(result["data_schema"].schema.keys())
        gradual_rate_field = next(
            (key for key in schema_keys if str(key) == CONF_GRADUAL_ADJUSTMENT_RATE),
            None
        )
        assert gradual_rate_field is not None
    
    async def test_config_flow_gradual_adjustment_rate_validation(self, mock_hass):
        """Test gradual adjustment rate validation (0.1-2.0°C range)."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        # Test valid values
        for valid_rate in [0.1, 0.5, 1.0, 1.5, 2.0]:
            result = await flow.async_step_user(user_input={
                CONF_NAME: "Test Climate",
                CONF_CLIMATE_ENTITY: "climate.test",
                CONF_ROOM_SENSOR: "sensor.test_temp",
                CONF_GRADUAL_ADJUSTMENT_RATE: valid_rate,
            })
            
            # Should proceed to create entry (not show form again)
            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result["data"][CONF_GRADUAL_ADJUSTMENT_RATE] == valid_rate
    
    async def test_config_flow_gradual_adjustment_rate_invalid_low(self, mock_hass):
        """Test gradual adjustment rate validation rejects values below 0.1."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        # Test invalid low value
        with pytest.raises(vol.Invalid):
            await flow.async_step_user(user_input={
                CONF_NAME: "Test Climate",
                CONF_CLIMATE_ENTITY: "climate.test",
                CONF_ROOM_SENSOR: "sensor.test_temp",
                CONF_GRADUAL_ADJUSTMENT_RATE: 0.05,  # Too low
            })
    
    async def test_config_flow_gradual_adjustment_rate_invalid_high(self, mock_hass):
        """Test gradual adjustment rate validation rejects values above 2.0."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        # Test invalid high value
        with pytest.raises(vol.Invalid):
            await flow.async_step_user(user_input={
                CONF_NAME: "Test Climate",
                CONF_CLIMATE_ENTITY: "climate.test",
                CONF_ROOM_SENSOR: "sensor.test_temp",
                CONF_GRADUAL_ADJUSTMENT_RATE: 2.5,  # Too high
            })
    
    async def test_config_flow_gradual_adjustment_rate_default(self, mock_hass):
        """Test gradual adjustment rate default value."""
        flow = SmartClimateConfigFlow()
        flow.hass = mock_hass
        
        # Get the form
        result = await flow.async_step_user()
        
        # Check default value in schema
        schema = result["data_schema"]
        gradual_rate_field = next(
            (key for key in schema.schema.keys() if str(key) == CONF_GRADUAL_ADJUSTMENT_RATE),
            None
        )
        
        # The default should be set
        assert gradual_rate_field.default() == DEFAULT_GRADUAL_ADJUSTMENT_RATE


class TestTemperatureControllerWithCustomRate:
    """Test TemperatureController with custom gradual adjustment rates."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        hass = Mock()
        hass.services = Mock()
        hass.services.async_call = AsyncMock()
        return hass
    
    @pytest.fixture
    def limits(self):
        """Temperature limits fixture."""
        return TemperatureLimits(min_temperature=16.0, max_temperature=30.0)
    
    @pytest.fixture
    def mode_adjustments(self):
        """ModeAdjustments fixture."""
        return ModeAdjustments(
            temperature_override=None,
            offset_adjustment=0.0,
            update_interval_override=None,
            boost_offset=0.0
        )
    
    def test_controller_init_with_custom_rate(self, mock_hass, limits):
        """Test TemperatureController initialization with custom rate."""
        custom_rate = 1.0
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=custom_rate
        )
        
        assert controller._hass == mock_hass
        assert controller._limits == limits
        assert controller._gradual_adjustment_rate == custom_rate
        assert controller._last_adjustment == 0.0
    
    def test_controller_init_without_rate_uses_default(self, mock_hass, limits):
        """Test TemperatureController uses default rate when not specified."""
        controller = TemperatureController(mock_hass, limits)
        
        assert controller._gradual_adjustment_rate == DEFAULT_GRADUAL_ADJUSTMENT_RATE
    
    def test_gradual_adjustment_with_rate_0_1(self, mock_hass, limits):
        """Test gradual adjustment with 0.1°C rate (slowest)."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.1
        )
        
        # Test small increase
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.0,
            target_adjustment=1.5
        )
        # Should be limited to 0.1°C increase
        assert result == 1.1
        
        # Test small decrease
        result = controller.apply_gradual_adjustment(
            current_adjustment=2.0,
            target_adjustment=1.0
        )
        # Should be limited to 0.1°C decrease
        assert result == 1.9
    
    def test_gradual_adjustment_with_rate_0_5(self, mock_hass, limits):
        """Test gradual adjustment with 0.5°C rate (default)."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.5
        )
        
        # Test medium increase
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.0,
            target_adjustment=2.5
        )
        # Should be limited to 0.5°C increase
        assert result == 1.5
        
        # Test medium decrease
        result = controller.apply_gradual_adjustment(
            current_adjustment=3.0,
            target_adjustment=1.0
        )
        # Should be limited to 0.5°C decrease
        assert result == 2.5
    
    def test_gradual_adjustment_with_rate_1_0(self, mock_hass, limits):
        """Test gradual adjustment with 1.0°C rate (faster)."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=1.0
        )
        
        # Test large increase
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.0,
            target_adjustment=3.0
        )
        # Should be limited to 1.0°C increase
        assert result == 2.0
        
        # Test large decrease
        result = controller.apply_gradual_adjustment(
            current_adjustment=4.0,
            target_adjustment=1.0
        )
        # Should be limited to 1.0°C decrease
        assert result == 3.0
    
    def test_gradual_adjustment_with_rate_2_0(self, mock_hass, limits):
        """Test gradual adjustment with 2.0°C rate (fastest)."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=2.0
        )
        
        # Test very large increase
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.0,
            target_adjustment=4.0
        )
        # Should be limited to 2.0°C increase
        assert result == 3.0
        
        # Test very large decrease
        result = controller.apply_gradual_adjustment(
            current_adjustment=5.0,
            target_adjustment=1.0
        )
        # Should be limited to 2.0°C decrease
        assert result == 3.0
    
    def test_gradual_adjustment_within_rate_limit(self, mock_hass, limits):
        """Test gradual adjustment when change is within rate limit."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=1.0
        )
        
        # Test change smaller than rate limit
        result = controller.apply_gradual_adjustment(
            current_adjustment=2.0,
            target_adjustment=2.5
        )
        # Should apply full change (0.5 < 1.0)
        assert result == 2.5
        
        # Test exact rate limit
        result = controller.apply_gradual_adjustment(
            current_adjustment=2.0,
            target_adjustment=3.0
        )
        # Should apply full change (1.0 = 1.0)
        assert result == 3.0
    
    def test_gradual_adjustment_no_change(self, mock_hass, limits):
        """Test gradual adjustment with no change needed."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.5
        )
        
        result = controller.apply_gradual_adjustment(
            current_adjustment=2.0,
            target_adjustment=2.0
        )
        # Should return same value
        assert result == 2.0
    
    def test_temperature_control_integration_with_custom_rate(self, mock_hass, limits, mode_adjustments):
        """Test complete temperature control flow with custom rate."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.2
        )
        
        # First update - limited by rate
        controller._last_adjustment = 0.0
        target_offset = 1.0
        
        # Apply gradual adjustment
        gradual_offset = controller.apply_gradual_adjustment(
            controller._last_adjustment,
            target_offset
        )
        assert gradual_offset == 0.2  # Limited by 0.2°C rate
        
        # Apply to temperature
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=gradual_offset,
            mode_adjustments=mode_adjustments
        )
        assert result == 22.2  # 22.0 + 0.2
        
        # Update last adjustment
        controller._last_adjustment = gradual_offset
        
        # Second update - still limited by rate
        gradual_offset = controller.apply_gradual_adjustment(
            controller._last_adjustment,
            target_offset
        )
        assert gradual_offset == 0.4  # 0.2 + 0.2
        
        # Apply to temperature
        result = controller.apply_offset_and_limits(
            target_temp=22.0,
            offset=gradual_offset,
            mode_adjustments=mode_adjustments
        )
        assert result == 22.4  # 22.0 + 0.4


class TestBackwardCompatibility:
    """Test backward compatibility for configurations without gradual_adjustment_rate."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        hass = Mock()
        hass.services = Mock()
        hass.services.async_call = AsyncMock()
        return hass
    
    @pytest.fixture
    def limits(self):
        """Temperature limits fixture."""
        return TemperatureLimits(min_temperature=16.0, max_temperature=30.0)
    
    def test_controller_backward_compatibility(self, mock_hass, limits):
        """Test controller works with old config missing gradual_adjustment_rate."""
        # Simulate old configuration without the parameter
        controller = TemperatureController(mock_hass, limits)
        
        # Should use default rate
        assert controller._gradual_adjustment_rate == DEFAULT_GRADUAL_ADJUSTMENT_RATE
        
        # Should work normally
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.0,
            target_adjustment=2.0
        )
        assert result == 1.5  # 1.0 + 0.5 (default rate)
    
    async def test_config_entry_migration(self, mock_hass):
        """Test config entry without gradual_adjustment_rate uses default."""
        # Simulate old config entry
        old_config = {
            CONF_NAME: "Test Climate",
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.test_temp",
            # No CONF_GRADUAL_ADJUSTMENT_RATE
        }
        
        # When accessed, should provide default
        rate = old_config.get(CONF_GRADUAL_ADJUSTMENT_RATE, DEFAULT_GRADUAL_ADJUSTMENT_RATE)
        assert rate == DEFAULT_GRADUAL_ADJUSTMENT_RATE


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def mock_hass(self):
        """Mock HomeAssistant instance."""
        hass = Mock()
        hass.services = Mock()
        hass.services.async_call = AsyncMock()
        return hass
    
    @pytest.fixture
    def limits(self):
        """Temperature limits fixture."""
        return TemperatureLimits(min_temperature=16.0, max_temperature=30.0)
    
    def test_very_small_adjustments(self, mock_hass, limits):
        """Test handling of very small adjustments."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.1
        )
        
        # Test tiny change smaller than rate
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.0,
            target_adjustment=1.05
        )
        # Should apply full change since it's smaller than rate
        assert result == 1.05
    
    def test_negative_adjustments(self, mock_hass, limits):
        """Test handling of negative adjustments."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.5
        )
        
        # Test negative current adjustment
        result = controller.apply_gradual_adjustment(
            current_adjustment=-2.0,
            target_adjustment=0.0
        )
        # Should increase by rate limit
        assert result == -1.5
        
        # Test negative target adjustment
        result = controller.apply_gradual_adjustment(
            current_adjustment=0.0,
            target_adjustment=-2.0
        )
        # Should decrease by rate limit
        assert result == -0.5
    
    def test_floating_point_precision(self, mock_hass, limits):
        """Test handling of floating point precision."""
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.3
        )
        
        # Test with values that might cause precision issues
        result = controller.apply_gradual_adjustment(
            current_adjustment=1.1,
            target_adjustment=1.7
        )
        # Should be 1.1 + 0.3 = 1.4
        assert abs(result - 1.4) < 0.0001  # Allow for tiny floating point errors
    
    def test_boundary_values(self, mock_hass, limits):
        """Test boundary values for rate limits."""
        # Test minimum rate
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=0.1
        )
        assert controller._gradual_adjustment_rate == 0.1
        
        # Test maximum rate
        controller = TemperatureController(
            mock_hass, 
            limits, 
            gradual_adjustment_rate=2.0
        )
        assert controller._gradual_adjustment_rate == 2.0