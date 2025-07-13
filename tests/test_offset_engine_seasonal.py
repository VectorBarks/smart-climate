"""Tests for OffsetEngine seasonal adaptation enhancements.

ABOUTME: Comprehensive test suite for OffsetEngine integration with SeasonalHysteresisLearner.
Tests seasonal offset calculation, backward compatibility, and enhanced prediction accuracy.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, time
import logging

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.seasonal_learner import SeasonalHysteresisLearner
from custom_components.smart_climate.models import OffsetInput
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    hass_mock = Mock()
    hass_mock.states = Mock()
    return hass_mock


@pytest.fixture
def config_with_outdoor_sensor():
    """Configuration with outdoor sensor for seasonal features."""
    return {
        "max_offset": 5.0,
        "ml_enabled": True,
        "enable_learning": True,
        "outdoor_sensor": "sensor.outdoor_temp",
        "power_sensor": "sensor.ac_power"
    }


@pytest.fixture
def config_without_outdoor_sensor():
    """Configuration without outdoor sensor - no seasonal features."""
    return {
        "max_offset": 5.0,
        "ml_enabled": True,
        "enable_learning": True,
        "power_sensor": "sensor.ac_power"
    }


@pytest.fixture
def seasonal_learner_mock(hass):
    """Mock seasonal learner with test data."""
    learner = Mock()
    learner.get_relevant_hysteresis_delta.return_value = 2.5
    return learner


@pytest.fixture
def offset_input_with_outdoor():
    """OffsetInput with outdoor temperature."""
    return OffsetInput(
        ac_internal_temp=25.0,
        room_temp=24.0,
        outdoor_temp=30.0,
        mode="normal",
        power_consumption=1500.0,
        time_of_day=time(14, 30),
        day_of_week=2
    )


@pytest.fixture
def offset_input_without_outdoor():
    """OffsetInput without outdoor temperature."""
    return OffsetInput(
        ac_internal_temp=25.0,
        room_temp=24.0,
        outdoor_temp=None,
        mode="normal",
        power_consumption=1500.0,
        time_of_day=time(14, 30),
        day_of_week=2
    )


class TestOffsetEngineSeasonalIntegration:
    """Test seasonal learner integration into OffsetEngine."""
    
    def test_offset_engine_init_with_seasonal_learner(self, hass, config_with_outdoor_sensor):
        """Test OffsetEngine initialization with seasonal learner."""
        # Test that OffsetEngine can be initialized with seasonal_learner parameter
        seasonal_learner = Mock()
        
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner)
        
        assert hasattr(engine, '_seasonal_learner')
        assert engine._seasonal_learner is seasonal_learner
        assert engine._seasonal_features_enabled is True
    
    def test_offset_engine_init_without_seasonal_learner(self, config_without_outdoor_sensor):
        """Test OffsetEngine initialization without seasonal learner (backward compatibility)."""
        # Test backward compatibility - should work without seasonal_learner parameter
        engine = OffsetEngine(config_without_outdoor_sensor)
        
        assert hasattr(engine, '_seasonal_learner')
        assert engine._seasonal_learner is None
        assert engine._seasonal_features_enabled is False
    
    def test_offset_engine_init_with_none_seasonal_learner(self, config_with_outdoor_sensor):
        """Test OffsetEngine initialization with explicit None seasonal learner."""
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=None)
        
        assert engine._seasonal_learner is None
        assert engine._seasonal_features_enabled is False
    
    def test_get_predicted_hysteresis_delta_with_seasonal_context(self, hass, config_with_outdoor_sensor, seasonal_learner_mock):
        """Test enhanced hysteresis prediction with seasonal context."""
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner_mock)
        
        # Mock outdoor temperature
        seasonal_learner_mock.get_relevant_hysteresis_delta.return_value = 2.8
        
        result = engine.get_predicted_hysteresis_delta(outdoor_temp=30.0)
        
        assert result == 2.8
        seasonal_learner_mock.get_relevant_hysteresis_delta.assert_called_once_with(30.0)
    
    def test_get_predicted_hysteresis_delta_fallback_to_traditional(self, config_without_outdoor_sensor):
        """Test fallback to traditional hysteresis when no seasonal learner."""
        engine = OffsetEngine(config_without_outdoor_sensor)
        
        # Should fall back to traditional HysteresisLearner behavior
        result = engine.get_predicted_hysteresis_delta(outdoor_temp=30.0)
        
        # Without sufficient traditional hysteresis data, should return None
        assert result is None
    
    def test_calculate_seasonal_offset_with_outdoor_temp(self, config_with_outdoor_sensor, seasonal_learner_mock):
        """Test seasonal offset calculation with outdoor temperature context."""
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner_mock)
        
        # Mock seasonal prediction
        seasonal_learner_mock.get_relevant_hysteresis_delta.return_value = 2.5
        
        result = engine.calculate_seasonal_offset(
            room_temp=24.0, 
            ac_temp=25.0, 
            outdoor_temp=30.0
        )
        
        # Should return seasonally-adjusted offset
        assert isinstance(result, float)
        # The result should be influenced by seasonal context
        assert result != 1.0  # Not just the basic difference
    
    def test_calculate_seasonal_offset_without_outdoor_temp(self, config_with_outdoor_sensor, seasonal_learner_mock):
        """Test seasonal offset calculation gracefully handles missing outdoor temp."""
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner_mock)
        
        result = engine.calculate_seasonal_offset(
            room_temp=24.0, 
            ac_temp=25.0, 
            outdoor_temp=None
        )
        
        # Should fall back to basic calculation
        assert result == 1.0  # Basic AC temp - room temp
    
    def test_calculate_seasonal_offset_no_seasonal_learner(self, config_without_outdoor_sensor):
        """Test seasonal offset calculation without seasonal learner (backward compatibility)."""
        engine = OffsetEngine(config_without_outdoor_sensor)
        
        result = engine.calculate_seasonal_offset(
            room_temp=24.0, 
            ac_temp=25.0, 
            outdoor_temp=30.0
        )
        
        # Should fall back to basic calculation
        assert result == 1.0  # Basic AC temp - room temp
    
    def test_calculate_offset_uses_seasonal_context(self, seasonal_learner_mock, offset_input_with_outdoor):
        """Test main calculate_offset method integrates seasonal context."""
        # Use config without learning to avoid calibration phase
        config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": False,  # Disable learning to avoid calibration
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.ac_power"
        }
        engine = OffsetEngine(config, seasonal_learner=seasonal_learner_mock)
        
        # Mock seasonal prediction
        seasonal_learner_mock.get_relevant_hysteresis_delta.return_value = 2.5
        
        result = engine.calculate_offset(offset_input_with_outdoor)
        
        assert result.offset != 1.0  # Should be different from basic calculation
        assert "seasonal" in result.reason.lower() or "enhanced" in result.reason.lower()
        assert result.confidence > 0.5  # Should have good confidence with seasonal data
    
    def test_calculate_offset_backward_compatibility(self, config_without_outdoor_sensor, offset_input_without_outdoor):
        """Test calculate_offset maintains backward compatibility without seasonal features."""
        engine = OffsetEngine(config_without_outdoor_sensor)
        
        result = engine.calculate_offset(offset_input_without_outdoor)
        
        # Should work exactly as before
        assert isinstance(result.offset, float)
        assert isinstance(result.confidence, float)
        assert "seasonal" not in result.reason.lower()
    
    def test_seasonal_features_detection(self, hass, config_with_outdoor_sensor):
        """Test proper detection of seasonal features availability."""
        # With outdoor sensor and seasonal learner
        seasonal_learner = Mock()
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner)
        assert engine._seasonal_features_enabled is True
        
        # Without seasonal learner
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=None)
        assert engine._seasonal_features_enabled is False
    
    def test_outdoor_sensor_handling(self, config_with_outdoor_sensor, seasonal_learner_mock, offset_input_with_outdoor):
        """Test handling of outdoor sensor data in seasonal calculations."""
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner_mock)
        
        # Test with outdoor temperature available
        offset_input_with_outdoor.outdoor_temp = 32.0
        result = engine.calculate_offset(offset_input_with_outdoor)
        
        # Should call seasonal learner with outdoor temp
        seasonal_learner_mock.get_relevant_hysteresis_delta.assert_called()
        
        # Test with outdoor temperature unavailable
        offset_input_with_outdoor.outdoor_temp = None
        result = engine.calculate_offset(offset_input_with_outdoor)
        
        # Should still work (graceful degradation)
        assert isinstance(result.offset, float)
    
    def test_logging_seasonal_vs_traditional(self, config_with_outdoor_sensor, seasonal_learner_mock, offset_input_with_outdoor, caplog):
        """Test appropriate logging distinguishes seasonal vs traditional operation."""
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner_mock)
        
        with caplog.at_level(logging.DEBUG):
            engine.calculate_offset(offset_input_with_outdoor)
        
        # Should log seasonal operation mode
        log_messages = caplog.text.lower()
        assert "seasonal" in log_messages or "enhanced" in log_messages


class TestSeasonalOffsetAccuracy:
    """Test seasonal offset calculation accuracy improvements."""
    
    @pytest.fixture
    def engine_with_seasonal_data(self):
        """OffsetEngine with seasonal learner containing realistic data."""
        config = {
            "max_offset": 5.0,
            "ml_enabled": True,
            "enable_learning": False,  # Disable learning to avoid calibration
            "outdoor_sensor": "sensor.outdoor_temp"
        }
        
        seasonal_learner = Mock()
        # Mock realistic seasonal predictions based on outdoor temp
        def seasonal_prediction(outdoor_temp):
            if outdoor_temp is None:
                return None
            elif outdoor_temp > 35:
                return 3.2  # Hot weather needs more cooling
            elif outdoor_temp > 25:
                return 2.5  # Moderate weather
            else:
                return 1.8  # Cool weather needs less cooling
        
        seasonal_learner.get_relevant_hysteresis_delta.side_effect = seasonal_prediction
        
        return OffsetEngine(config, seasonal_learner=seasonal_learner)
    
    def test_hot_weather_enhanced_prediction(self, engine_with_seasonal_data):
        """Test enhanced predictions for hot weather conditions."""
        offset_input = OffsetInput(
            ac_internal_temp=26.0,
            room_temp=25.0,
            outdoor_temp=38.0,  # Very hot outside
            mode="normal",
            power_consumption=2000.0,
            time_of_day=time(15, 0),
            day_of_week=3
        )
        
        result = engine_with_seasonal_data.calculate_offset(offset_input)
        
        # Should provide enhanced offset for hot conditions
        assert result.offset != 1.0  # Not just basic calculation
        assert result.confidence > 0.6  # High confidence with seasonal context
    
    def test_cool_weather_enhanced_prediction(self, engine_with_seasonal_data):
        """Test enhanced predictions for cool weather conditions."""
        offset_input = OffsetInput(
            ac_internal_temp=26.0,
            room_temp=25.0,
            outdoor_temp=20.0,  # Cool outside
            mode="normal",
            power_consumption=800.0,
            time_of_day=time(10, 0),
            day_of_week=1
        )
        
        result = engine_with_seasonal_data.calculate_offset(offset_input)
        
        # Should provide different offset for cool conditions
        assert result.offset != 1.0  # Not just basic calculation
        assert result.confidence > 0.6  # High confidence with seasonal context
    
    def test_seasonal_vs_traditional_comparison(self):
        """Test that seasonal predictions differ appropriately from traditional ones."""
        config = {"max_offset": 5.0, "enable_learning": False}
        
        # Traditional engine (no seasonal features)
        traditional_engine = OffsetEngine(config)
        
        # Seasonal engine with data
        seasonal_learner = Mock()
        seasonal_learner.get_relevant_hysteresis_delta.return_value = 3.0
        seasonal_engine = OffsetEngine(config, seasonal_learner=seasonal_learner)
        
        offset_input = OffsetInput(
            ac_internal_temp=26.0,
            room_temp=25.0,
            outdoor_temp=35.0,
            mode="normal",
            power_consumption=1800.0,
            time_of_day=time(14, 0),
            day_of_week=2
        )
        
        traditional_result = traditional_engine.calculate_offset(offset_input)
        seasonal_result = seasonal_engine.calculate_offset(offset_input)
        
        # Results should differ when seasonal data is available
        assert seasonal_result.offset != traditional_result.offset
        assert seasonal_result.confidence >= traditional_result.confidence


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for seasonal integration."""
    
    def test_seasonal_learner_exception_handling(self, config_with_outdoor_sensor):
        """Test graceful handling of seasonal learner exceptions."""
        seasonal_learner = Mock()
        seasonal_learner.get_relevant_hysteresis_delta.side_effect = Exception("Seasonal learner error")
        
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner)
        
        offset_input = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=1500.0,
            time_of_day=time(14, 30),
            day_of_week=2
        )
        
        # Should not raise exception, fall back gracefully
        result = engine.calculate_offset(offset_input)
        assert isinstance(result.offset, float)
        assert result.confidence >= 0.0
    
    def test_invalid_outdoor_temperature_values(self, config_with_outdoor_sensor, seasonal_learner_mock):
        """Test handling of invalid outdoor temperature values."""
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner_mock)
        
        invalid_temps = [float('inf'), float('-inf'), float('nan')]
        
        for invalid_temp in invalid_temps:
            offset_input = OffsetInput(
                ac_internal_temp=25.0,
                room_temp=24.0,
                outdoor_temp=invalid_temp,
                mode="normal",
                power_consumption=1500.0,
                time_of_day=time(14, 30),
                day_of_week=2
            )
            
            # Should handle gracefully
            result = engine.calculate_offset(offset_input)
            assert isinstance(result.offset, float)
            assert not any(x in str(result.offset) for x in ['inf', 'nan'])
    
    def test_seasonal_learner_none_return(self, config_with_outdoor_sensor):
        """Test handling when seasonal learner returns None."""
        seasonal_learner = Mock()
        seasonal_learner.get_relevant_hysteresis_delta.return_value = None
        
        engine = OffsetEngine(config_with_outdoor_sensor, seasonal_learner=seasonal_learner)
        
        offset_input = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="normal",
            power_consumption=1500.0,
            time_of_day=time(14, 30),
            day_of_week=2
        )
        
        result = engine.calculate_offset(offset_input)
        
        # Should fall back to traditional calculation
        assert isinstance(result.offset, float)
        assert result.confidence >= 0.0
    
    def test_configuration_edge_cases(self):
        """Test edge cases in configuration handling."""
        # Empty config
        engine = OffsetEngine({})
        assert engine._seasonal_features_enabled is False
        
        # Config with only outdoor sensor but no seasonal learner
        config = {"outdoor_sensor": "sensor.outdoor_temp"}
        engine = OffsetEngine(config)
        assert engine._seasonal_features_enabled is False
        
        # Config with seasonal learner but no outdoor sensor in config
        config = {}
        seasonal_learner = Mock()
        engine = OffsetEngine(config, seasonal_learner=seasonal_learner)
        assert engine._seasonal_features_enabled is True  # Learner presence enables features


class TestBackwardCompatibility:
    """Comprehensive backward compatibility tests."""
    
    def test_existing_api_unchanged(self):
        """Test that existing OffsetEngine API remains unchanged."""
        # All existing methods should still exist
        config = {"max_offset": 5.0}
        engine = OffsetEngine(config)
        
        # Check that all original methods exist
        assert hasattr(engine, 'calculate_offset')
        assert hasattr(engine, 'get_learning_info')
        assert hasattr(engine, 'enable_learning')
        assert hasattr(engine, 'disable_learning')
        assert hasattr(engine, 'record_feedback')
        assert hasattr(engine, 'record_actual_performance')
    
    def test_original_initialization_patterns(self):
        """Test that original initialization patterns still work."""
        # Original pattern: just config
        config = {"max_offset": 3.0, "enable_learning": True}
        engine = OffsetEngine(config)
        assert engine._max_offset == 3.0
        
        # Should work exactly as before
        offset_input = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=None,  # Original usage often had None
            mode="normal",
            power_consumption=None,  # Original usage often had None
            time_of_day=time(12, 0),
            day_of_week=1
        )
        
        result = engine.calculate_offset(offset_input)
        assert isinstance(result.offset, float)
        assert result.offset == 1.0  # Should be basic calculation
    
    def test_learning_functionality_preserved(self):
        """Test that learning functionality works as before when no seasonal features."""
        config = {"max_offset": 5.0, "enable_learning": True}
        engine = OffsetEngine(config)
        
        # Enable/disable should work as before
        engine.enable_learning()
        assert engine.is_learning_enabled is True
        
        engine.disable_learning()
        assert engine.is_learning_enabled is False
        
        # Learning info should work as before
        info = engine.get_learning_info()
        assert isinstance(info, dict)
        assert "enabled" in info
    
    def test_no_new_required_parameters(self):
        """Test that no new required parameters were introduced."""
        # Should be able to create with minimal config
        engine = OffsetEngine({})
        
        # Should be able to calculate offset with minimal input
        offset_input = OffsetInput(
            ac_internal_temp=25.0,
            room_temp=24.0,
            outdoor_temp=None,
            mode="normal",
            power_consumption=None,
            time_of_day=time(12, 0),
            day_of_week=1
        )
        
        result = engine.calculate_offset(offset_input)
        assert isinstance(result.offset, float)