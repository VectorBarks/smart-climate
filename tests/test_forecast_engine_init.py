"""ABOUTME: Tests for ForecastEngine initialization with various configurations.
Validates all initialization scenarios including valid configs, missing entities, and edge cases."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from typing import Dict, Any, List

from custom_components.smart_climate.forecast_engine import ForecastEngine
from custom_components.smart_climate.models import Forecast, ActiveStrategy


class TestForecastEngineInitialization:
    """Test ForecastEngine initialization with various configurations."""

    def test_init_with_valid_predictive_config(self):
        """Test ForecastEngine initialization with valid predictive configuration."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": [
                {
                    "name": "heat_wave",
                    "enabled": True,
                    "type": "heat_wave",
                    "temp_threshold": 30.0,
                    "min_duration_hours": 3,
                    "lookahead_hours": 24,
                    "pre_action_hours": 2,
                    "adjustment": -2.0
                },
                {
                    "name": "clear_sky",
                    "enabled": True,
                    "type": "clear_sky",
                    "condition": "sunny",
                    "min_duration_hours": 2,
                    "lookahead_hours": 12,
                    "pre_action_hours": 1,
                    "adjustment": -1.0
                }
            ]
        }
        
        engine = ForecastEngine(hass, config)
        
        assert engine._hass is hass
        assert engine._weather_entity == "weather.home"
        assert len(engine._strategies) == 2
        assert engine._strategies[0]["name"] == "heat_wave"
        assert engine._strategies[1]["name"] == "clear_sky"
        assert engine._forecast_data == []
        assert engine._active_strategy is None
        assert engine._last_update is None

    def test_init_with_missing_weather_entity(self):
        """Test ForecastEngine initialization without weather entity."""
        hass = Mock()
        config = {
            "strategies": [
                {
                    "name": "heat_wave",
                    "enabled": True,
                    "type": "heat_wave"
                }
            ]
        }
        
        engine = ForecastEngine(hass, config)
        
        assert engine._weather_entity is None
        assert len(engine._strategies) == 1

    def test_init_with_empty_strategies_array(self):
        """Test ForecastEngine initialization with empty strategies array."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": []
        }
        
        engine = ForecastEngine(hass, config)
        
        assert engine._weather_entity == "weather.home"
        assert engine._strategies == []

    def test_init_filters_disabled_strategies(self):
        """Test that ForecastEngine filters out disabled strategies."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": [
                {
                    "name": "heat_wave",
                    "enabled": True,
                    "type": "heat_wave"
                },
                {
                    "name": "cold_snap",
                    "enabled": False,
                    "type": "cold_snap"
                },
                {
                    "name": "clear_sky",
                    "enabled": True,
                    "type": "clear_sky"
                }
            ]
        }
        
        engine = ForecastEngine(hass, config)
        
        assert len(engine._strategies) == 2
        assert engine._strategies[0]["name"] == "heat_wave"
        assert engine._strategies[1]["name"] == "clear_sky"
        # Disabled strategy should not be included
        assert not any(s["name"] == "cold_snap" for s in engine._strategies)

    def test_init_handles_missing_enabled_field(self):
        """Test that strategies without 'enabled' field default to enabled."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": [
                {
                    "name": "heat_wave",
                    "type": "heat_wave"
                },
                {
                    "name": "clear_sky",
                    "enabled": True,
                    "type": "clear_sky"
                }
            ]
        }
        
        engine = ForecastEngine(hass, config)
        
        # Both strategies should be included (default enabled=True)
        assert len(engine._strategies) == 2

    def test_init_with_minimal_config(self):
        """Test ForecastEngine initialization with minimal configuration."""
        hass = Mock()
        config = {}
        
        engine = ForecastEngine(hass, config)
        
        assert engine._weather_entity is None
        assert engine._strategies == []
        assert engine._update_interval == timedelta(minutes=30)

    def test_init_with_none_strategies(self):
        """Test ForecastEngine initialization when strategies is None."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": None
        }
        
        # This should raise TypeError due to None not being iterable
        with pytest.raises(TypeError):
            engine = ForecastEngine(hass, config)

    @pytest.mark.parametrize("strategy_config,expected_fields", [
        (
            {
                "name": "heat_wave",
                "enabled": True,
                "type": "heat_wave",
                "temp_threshold": 35.0,
                "min_duration_hours": 4,
                "lookahead_hours": 48,
                "pre_action_hours": 3,
                "adjustment": -3.0
            },
            {
                "temp_threshold": 35.0,
                "min_duration_hours": 4,
                "lookahead_hours": 48,
                "pre_action_hours": 3,
                "adjustment": -3.0
            }
        ),
        (
            {
                "name": "clear_sky",
                "enabled": True,
                "type": "clear_sky",
                "condition": "partlycloudy",
                "min_duration_hours": 1,
                "lookahead_hours": 6,
                "pre_action_hours": 0.5,
                "adjustment": -0.5
            },
            {
                "condition": "partlycloudy",
                "min_duration_hours": 1,
                "lookahead_hours": 6,
                "pre_action_hours": 0.5,
                "adjustment": -0.5
            }
        )
    ])
    def test_strategy_parameters_preserved(self, strategy_config, expected_fields):
        """Test that all strategy parameters are preserved during initialization."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": [strategy_config]
        }
        
        engine = ForecastEngine(hass, config)
        
        assert len(engine._strategies) == 1
        strategy = engine._strategies[0]
        
        for field, expected_value in expected_fields.items():
            assert strategy[field] == expected_value

    def test_init_with_mixed_strategy_states(self):
        """Test initialization with various strategy enabled states."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": [
                {"name": "s1", "enabled": True},
                {"name": "s2", "enabled": False},
                {"name": "s3"},  # Default to enabled
                {"name": "s4", "enabled": True},
                {"name": "s5", "enabled": False},
            ]
        }
        
        engine = ForecastEngine(hass, config)
        
        # Should have 3 enabled strategies (s1, s3, s4)
        assert len(engine._strategies) == 3
        enabled_names = [s["name"] for s in engine._strategies]
        assert "s1" in enabled_names
        assert "s3" in enabled_names
        assert "s4" in enabled_names
        assert "s2" not in enabled_names
        assert "s5" not in enabled_names

    def test_predictive_offset_initial_state(self):
        """Test predictive_offset property returns 0.0 initially."""
        hass = Mock()
        config = {"weather_entity": "weather.home"}
        
        engine = ForecastEngine(hass, config)
        
        assert engine.predictive_offset == 0.0

    def test_active_strategy_info_initial_state(self):
        """Test active_strategy_info property returns None initially."""
        hass = Mock()
        config = {"weather_entity": "weather.home"}
        
        engine = ForecastEngine(hass, config)
        
        assert engine.active_strategy_info is None

    @pytest.mark.asyncio
    async def test_async_update_without_weather_entity(self):
        """Test async_update returns early when no weather entity configured."""
        hass = Mock()
        config = {"strategies": []}
        
        engine = ForecastEngine(hass, config)
        
        # Should return without doing anything
        await engine.async_update()
        
        assert engine._last_update is None
        assert engine._forecast_data == []

    def test_complex_nested_config(self):
        """Test initialization with complex nested configuration."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home_assistant",
            "strategies": [
                {
                    "name": "extreme_heat",
                    "enabled": True,
                    "type": "heat_wave",
                    "temp_threshold": 40.0,
                    "min_duration_hours": 6,
                    "lookahead_hours": 72,
                    "pre_action_hours": 4,
                    "adjustment": -4.0,
                    "extra_field": "ignored"  # Extra fields should be preserved
                },
                {
                    "name": "mild_heat",
                    "enabled": True,
                    "type": "heat_wave",
                    "temp_threshold": 28.0,
                    "min_duration_hours": 2,
                    "lookahead_hours": 12,
                    "pre_action_hours": 1,
                    "adjustment": -1.5
                }
            ]
        }
        
        engine = ForecastEngine(hass, config)
        
        assert engine._weather_entity == "weather.home_assistant"
        assert len(engine._strategies) == 2
        
        # Verify extra fields are preserved
        assert engine._strategies[0]["extra_field"] == "ignored"
        
        # Verify all standard fields
        assert engine._strategies[0]["temp_threshold"] == 40.0
        assert engine._strategies[1]["temp_threshold"] == 28.0


class TestForecastEngineEdgeCases:
    """Test edge cases and error conditions for ForecastEngine initialization."""

    def test_init_with_invalid_types(self):
        """Test ForecastEngine handles invalid configuration types gracefully."""
        hass = Mock()
        
        # Test with string instead of list for strategies
        config = {
            "weather_entity": "weather.home",
            "strategies": "not_a_list"
        }
        
        # This should raise TypeError due to string not being iterable with .get method
        with pytest.raises(AttributeError):
            engine = ForecastEngine(hass, config)

    def test_init_with_malformed_strategy(self):
        """Test ForecastEngine handles malformed strategy configuration."""
        hass = Mock()
        config = {
            "weather_entity": "weather.home",
            "strategies": [
                {"name": "valid", "enabled": True},
                None,  # Invalid strategy
                {"name": "another_valid", "enabled": True}
            ]
        }
        
        # This should raise AttributeError due to None.get not existing
        with pytest.raises(AttributeError):
            engine = ForecastEngine(hass, config)

    def test_update_interval_constant(self):
        """Test that update interval is correctly set to 30 minutes."""
        hass = Mock()
        config = {}
        
        engine = ForecastEngine(hass, config)
        
        assert engine._update_interval == timedelta(minutes=30)
        assert engine._update_interval.total_seconds() == 1800  # 30 * 60

    def test_property_access_thread_safety(self):
        """Test that property access doesn't modify internal state."""
        hass = Mock()
        config = {"weather_entity": "weather.home"}
        
        engine = ForecastEngine(hass, config)
        
        # Access properties multiple times
        for _ in range(10):
            offset = engine.predictive_offset
            info = engine.active_strategy_info
        
        # State should remain unchanged
        assert engine._active_strategy is None
        assert engine._last_update is None
        assert engine.predictive_offset == 0.0
        assert engine.active_strategy_info is None