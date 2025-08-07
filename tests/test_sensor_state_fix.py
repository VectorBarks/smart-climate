"""Test sensor state fixes for weather forecast and seasonal adaptation sensors."""

import pytest
from unittest.mock import Mock, AsyncMock
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.const import CONF_FORECAST_ENABLED, CONF_OUTDOOR_SENSOR


class TestSensorStateFix:
    """Test cases for sensor state reporting fixes."""
    
    def test_weather_forecast_sensor_disabled_in_config(self):
        """Test WeatherForecastSensor shows correct state when forecast is disabled in config."""
        # Config with forecast_enabled = False
        config = {
            "max_offset": 5.0,
            CONF_FORECAST_ENABLED: False
        }
        
        # Mock forecast engine exists but config says disabled
        mock_forecast_engine = Mock()
        
        offset_engine = OffsetEngine(config=config)
        offset_engine.set_forecast_engine(mock_forecast_engine)
        
        # Test the logic directly - should be False because config disables it
        weather_forecast_state = offset_engine._weather_forecast_enabled and offset_engine._forecast_engine is not None
        assert weather_forecast_state is False
    
    def test_weather_forecast_sensor_enabled_in_config(self):
        """Test WeatherForecastSensor shows correct state when forecast is enabled in config."""
        # Config with forecast_enabled = True
        config = {
            "max_offset": 5.0,
            CONF_FORECAST_ENABLED: True
        }
        
        # Mock forecast engine exists
        mock_forecast_engine = Mock()
        
        offset_engine = OffsetEngine(config=config)
        offset_engine.set_forecast_engine(mock_forecast_engine)
        
        # Test the logic directly - should be True because both config AND engine exist
        weather_forecast_state = offset_engine._weather_forecast_enabled and offset_engine._forecast_engine is not None
        assert weather_forecast_state is True
    
    def test_weather_forecast_sensor_enabled_but_no_engine(self):
        """Test WeatherForecastSensor shows False when enabled in config but no engine."""
        # Config with forecast_enabled = True but no engine
        config = {
            "max_offset": 5.0,
            CONF_FORECAST_ENABLED: True
        }
        
        offset_engine = OffsetEngine(config=config)
        # No forecast engine set
        
        # Test the logic directly - should be False because no engine despite config
        weather_forecast_state = offset_engine._weather_forecast_enabled and offset_engine._forecast_engine is not None
        assert weather_forecast_state is False
    
    def test_seasonal_adaptation_sensor_no_outdoor_sensor(self):
        """Test SeasonalAdaptationSensor shows correct state when no outdoor sensor configured."""
        # Config with empty/None outdoor_sensor
        config = {
            "max_offset": 5.0,
            CONF_OUTDOOR_SENSOR: None
        }
        
        offset_engine = OffsetEngine(config=config)
        
        # Get seasonal data
        seasonal_data = offset_engine._get_seasonal_data()
        
        # Should be disabled because no outdoor sensor
        assert seasonal_data.enabled is False
    
    def test_seasonal_adaptation_sensor_empty_outdoor_sensor(self):
        """Test SeasonalAdaptationSensor shows correct state when outdoor sensor is empty string."""
        # Config with empty string outdoor_sensor
        config = {
            "max_offset": 5.0,
            CONF_OUTDOOR_SENSOR: ""
        }
        
        offset_engine = OffsetEngine(config=config)
        
        # Get seasonal data
        seasonal_data = offset_engine._get_seasonal_data()
        
        # Should be disabled because empty string
        assert seasonal_data.enabled is False
    
    def test_seasonal_adaptation_sensor_configured_outdoor_sensor(self):
        """Test SeasonalAdaptationSensor shows correct state when outdoor sensor is configured."""
        # Config with outdoor_sensor configured
        config = {
            "max_offset": 5.0,
            CONF_OUTDOOR_SENSOR: "sensor.outdoor_temp"
        }
        
        # Mock seasonal learner
        mock_seasonal_learner = Mock()
        mock_seasonal_learner.get_seasonal_contribution.return_value = 0.2
        mock_seasonal_learner.get_pattern_count.return_value = 5
        mock_seasonal_learner.get_outdoor_temp_bucket.return_value = "20-25°C"
        mock_seasonal_learner.get_accuracy.return_value = 0.8
        
        offset_engine = OffsetEngine(
            config=config,
            seasonal_learner=mock_seasonal_learner
        )
        
        # Get seasonal data
        seasonal_data = offset_engine._get_seasonal_data()
        
        # Should be enabled because outdoor sensor is configured AND learner exists
        assert seasonal_data.enabled is True
    
    def test_seasonal_adaptation_sensor_configured_but_no_learner(self):
        """Test SeasonalAdaptationSensor shows correct state when outdoor sensor configured but no learner."""
        # Config with outdoor_sensor configured
        config = {
            "max_offset": 5.0,
            CONF_OUTDOOR_SENSOR: "sensor.outdoor_temp"
        }
        
        # No seasonal learner passed
        offset_engine = OffsetEngine(config=config)
        
        # Get seasonal data
        seasonal_data = offset_engine._get_seasonal_data()
        
        # Should be disabled because no learner despite config
        assert seasonal_data.enabled is False

    def test_offset_engine_init_stores_weather_forecast_config(self):
        """Test that OffsetEngine stores weather forecast configuration during init."""
        config = {CONF_FORECAST_ENABLED: True}
        offset_engine = OffsetEngine(config=config)
        
        # Should store the config value
        assert hasattr(offset_engine, '_weather_forecast_enabled')
        assert offset_engine._weather_forecast_enabled is True

    def test_offset_engine_init_stores_seasonal_config(self):
        """Test that OffsetEngine stores seasonal configuration during init."""
        config = {"outdoor_sensor": "sensor.outdoor_temp"}
        offset_engine = OffsetEngine(config=config)
        
        # Should derive seasonal enabled from outdoor sensor config
        assert hasattr(offset_engine, '_seasonal_features_enabled')
        assert offset_engine._seasonal_features_enabled is True

    def test_offset_engine_init_defaults(self):
        """Test that OffsetEngine handles missing config keys with proper defaults."""
        config = {}  # Empty config
        offset_engine = OffsetEngine(config=config)
        
        # Should have defaults
        assert offset_engine._weather_forecast_enabled is False
        assert offset_engine._seasonal_features_enabled is False