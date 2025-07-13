"""
ABOUTME: Test suite for core intelligence attributes in Smart Climate entity.
Tests v1.3.0+ intelligence features exposed via extra_state_attributes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.delay_learner import DelayLearner
from custom_components.smart_climate.forecast_engine import ForecastEngine
from custom_components.smart_climate.models import ActiveStrategy
from tests.fixtures.mock_entities import (
    create_mock_hass,
    create_mock_offset_engine,
    create_mock_sensor_manager,
    create_mock_mode_manager,
    create_mock_temperature_controller,
    create_mock_coordinator
)


class TestCoreIntelligenceAttributes:
    """Test core intelligence attributes in extra_state_attributes."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        return create_mock_hass()

    @pytest.fixture  
    def mock_config(self):
        """Create a test configuration."""
        return {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.ac_power",
            "min_temperature": 16.0,
            "max_temperature": 30.0,
            "gradual_adjustment_rate": 0.5,
            "adaptive_delay": True,
            "delay_learning_timeout": 20
        }

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for SmartClimateEntity."""
        return {
            "offset_engine": create_mock_offset_engine(),
            "sensor_manager": create_mock_sensor_manager(),
            "mode_manager": create_mock_mode_manager(),
            "temperature_controller": create_mock_temperature_controller(),
            "coordinator": create_mock_coordinator()
        }

    @pytest.fixture
    def smart_climate_entity(self, mock_hass, mock_config, mock_dependencies):
        """Create a SmartClimateEntity with mocked dependencies."""
        entity = SmartClimateEntity(
            mock_hass,
            mock_config,
            "climate.test_ac",
            "sensor.room_temp",
            **mock_dependencies
        )
        return entity

    def test_adaptive_delay_with_delay_learner(self, smart_climate_entity):
        """Test adaptive_delay attribute when DelayLearner is available."""
        # Arrange: Setup DelayLearner mock
        mock_delay_learner = Mock(spec=DelayLearner)
        mock_delay_learner.get_adaptive_delay.return_value = 45
        smart_climate_entity._delay_learner = mock_delay_learner
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return learned delay
        assert "adaptive_delay" in attributes
        assert attributes["adaptive_delay"] == 45
        mock_delay_learner.get_adaptive_delay.assert_called_once()

    def test_adaptive_delay_without_delay_learner(self, smart_climate_entity):
        """Test adaptive_delay attribute when DelayLearner is not available."""
        # Arrange: No DelayLearner available
        smart_climate_entity._delay_learner = None
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return None (not available)
        assert "adaptive_delay" in attributes
        assert attributes["adaptive_delay"] is None

    def test_adaptive_delay_with_delay_learner_error(self, smart_climate_entity):
        """Test adaptive_delay attribute when DelayLearner raises exception."""
        # Arrange: DelayLearner that raises exception
        mock_delay_learner = Mock(spec=DelayLearner)
        mock_delay_learner.get_adaptive_delay.side_effect = Exception("Connection error")
        smart_climate_entity._delay_learner = mock_delay_learner
        
        # Act: Get attributes  
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should gracefully handle error and return None
        assert "adaptive_delay" in attributes
        assert attributes["adaptive_delay"] is None

    def test_weather_forecast_with_forecast_engine(self, smart_climate_entity):
        """Test weather_forecast attribute when ForecastEngine is available."""
        # Arrange: Setup ForecastEngine mock
        mock_forecast_engine = Mock(spec=ForecastEngine)
        mock_forecast_engine.predictive_offset = 0.0
        mock_forecast_engine.active_strategy_info = None
        smart_climate_entity._forecast_engine = mock_forecast_engine
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return True (weather forecast available)
        assert "weather_forecast" in attributes  
        assert attributes["weather_forecast"] is True

    def test_weather_forecast_without_forecast_engine(self, smart_climate_entity):
        """Test weather_forecast attribute when ForecastEngine is not available."""
        # Arrange: No ForecastEngine available
        smart_climate_entity._forecast_engine = None
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return False (no weather forecast)
        assert "weather_forecast" in attributes
        assert attributes["weather_forecast"] is False

    def test_seasonal_adaptation_with_offset_engine_seasonal_learner(self, smart_climate_entity):
        """Test seasonal_adaptation attribute when OffsetEngine has seasonal learner."""
        # Arrange: OffsetEngine with seasonal learner
        smart_climate_entity._offset_engine._seasonal_learner = Mock()
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return True (seasonal adaptation available)
        assert "seasonal_adaptation" in attributes
        assert attributes["seasonal_adaptation"] is True

    def test_seasonal_adaptation_without_seasonal_learner(self, smart_climate_entity):
        """Test seasonal_adaptation attribute when OffsetEngine has no seasonal learner."""
        # Arrange: OffsetEngine without seasonal learner
        smart_climate_entity._offset_engine._seasonal_learner = None
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return False (no seasonal adaptation)
        assert "seasonal_adaptation" in attributes
        assert attributes["seasonal_adaptation"] is False

    def test_seasonal_adaptation_with_missing_attribute(self, smart_climate_entity):
        """Test seasonal_adaptation when OffsetEngine doesn't have _seasonal_learner attribute."""
        # Arrange: OffsetEngine without _seasonal_learner attribute
        del smart_climate_entity._offset_engine._seasonal_learner
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should gracefully handle missing attribute and return False
        assert "seasonal_adaptation" in attributes
        assert attributes["seasonal_adaptation"] is False

    def test_seasonal_contribution_with_seasonal_data(self, smart_climate_entity):
        """Test seasonal_contribution attribute when seasonal data is available."""
        # Arrange: OffsetEngine with seasonal learner and contribution method
        mock_seasonal_learner = Mock()
        mock_seasonal_learner.get_seasonal_contribution.return_value = 75.5
        smart_climate_entity._offset_engine._seasonal_learner = mock_seasonal_learner
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return seasonal contribution percentage
        assert "seasonal_contribution" in attributes
        assert attributes["seasonal_contribution"] == 75.5

    def test_seasonal_contribution_without_seasonal_learner(self, smart_climate_entity):
        """Test seasonal_contribution attribute when no seasonal learner available."""
        # Arrange: No seasonal learner
        smart_climate_entity._offset_engine._seasonal_learner = None
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should return 0 (no seasonal contribution)
        assert "seasonal_contribution" in attributes
        assert attributes["seasonal_contribution"] == 0

    def test_seasonal_contribution_with_method_error(self, smart_climate_entity):
        """Test seasonal_contribution when seasonal learner method raises exception."""
        # Arrange: Seasonal learner with error-raising method
        mock_seasonal_learner = Mock()
        mock_seasonal_learner.get_seasonal_contribution.side_effect = Exception("Data error")
        smart_climate_entity._offset_engine._seasonal_learner = mock_seasonal_learner
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should gracefully handle error and return 0
        assert "seasonal_contribution" in attributes
        assert attributes["seasonal_contribution"] == 0

    def test_seasonal_contribution_without_method(self, smart_climate_entity):
        """Test seasonal_contribution when seasonal learner exists but lacks method."""
        # Arrange: Seasonal learner without get_seasonal_contribution method
        mock_seasonal_learner = Mock()
        del mock_seasonal_learner.get_seasonal_contribution
        smart_climate_entity._offset_engine._seasonal_learner = mock_seasonal_learner
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should gracefully handle missing method and return 0
        assert "seasonal_contribution" in attributes
        assert attributes["seasonal_contribution"] == 0

    def test_all_attributes_present_in_response(self, smart_climate_entity):
        """Test that all Phase 1 core intelligence attributes are always present."""
        # Arrange: Entity with no special components
        smart_climate_entity._delay_learner = None
        smart_climate_entity._forecast_engine = None
        smart_climate_entity._offset_engine._seasonal_learner = None
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: All Phase 1 attributes should be present
        required_attributes = [
            "adaptive_delay",
            "weather_forecast", 
            "seasonal_adaptation",
            "seasonal_contribution"
        ]
        
        for attr in required_attributes:
            assert attr in attributes, f"Required attribute '{attr}' missing from response"

    def test_existing_attributes_preserved(self, smart_climate_entity):
        """Test that existing attributes are preserved when adding new ones."""
        # Arrange: Set up existing attributes via last_offset and forecast_engine
        smart_climate_entity._last_offset = 2.5
        mock_forecast_engine = Mock(spec=ForecastEngine)
        mock_forecast_engine.predictive_offset = 1.0
        mock_forecast_engine.active_strategy_info = {
            "name": "heat_wave_precool",
            "adjustment": 1.0,
            "end_time": datetime.now().isoformat()
        }
        smart_climate_entity._forecast_engine = mock_forecast_engine
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Existing attributes should still be present
        assert "reactive_offset" in attributes
        assert attributes["reactive_offset"] == 2.5
        assert "predictive_offset" in attributes
        assert attributes["predictive_offset"] == 1.0
        assert "total_offset" in attributes
        assert attributes["total_offset"] == 3.5  # 2.5 + 1.0
        assert "predictive_strategy" in attributes

    def test_attribute_data_types(self, smart_climate_entity):
        """Test that all attributes return correct data types."""
        # Arrange: Set up components with known return types
        mock_delay_learner = Mock(spec=DelayLearner)
        mock_delay_learner.get_adaptive_delay.return_value = 45
        smart_climate_entity._delay_learner = mock_delay_learner
        
        mock_forecast_engine = Mock(spec=ForecastEngine)
        mock_forecast_engine.predictive_offset = 1.5
        mock_forecast_engine.active_strategy_info = None
        smart_climate_entity._forecast_engine = mock_forecast_engine
        
        mock_seasonal_learner = Mock()
        mock_seasonal_learner.get_seasonal_contribution.return_value = 65.0
        smart_climate_entity._offset_engine._seasonal_learner = mock_seasonal_learner
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Check data types
        assert isinstance(attributes["adaptive_delay"], int)
        assert isinstance(attributes["weather_forecast"], bool)
        assert isinstance(attributes["seasonal_adaptation"], bool)
        assert isinstance(attributes["seasonal_contribution"], (int, float))

    def test_performance_impact(self, smart_climate_entity):
        """Test that attribute calculation doesn't have significant performance impact."""
        # Arrange: Setup all components
        mock_delay_learner = Mock(spec=DelayLearner)
        mock_delay_learner.get_adaptive_delay.return_value = 45
        smart_climate_entity._delay_learner = mock_delay_learner
        
        mock_forecast_engine = Mock(spec=ForecastEngine)
        mock_forecast_engine.predictive_offset = 1.0
        mock_forecast_engine.active_strategy_info = None
        smart_climate_entity._forecast_engine = mock_forecast_engine
        
        mock_seasonal_learner = Mock()
        mock_seasonal_learner.get_seasonal_contribution.return_value = 75.0
        smart_climate_entity._offset_engine._seasonal_learner = mock_seasonal_learner
        
        # Act & Assert: Should complete quickly without expensive operations
        import time
        start_time = time.time()
        attributes = smart_climate_entity.extra_state_attributes
        elapsed_time = time.time() - start_time
        
        # Assert: Should complete in well under 10ms (0.01 seconds)
        assert elapsed_time < 0.01, f"Attribute calculation took {elapsed_time:.3f}s, should be <0.01s"
        assert len(attributes) >= 8  # At least 4 existing + 4 new attributes

    def test_integration_with_forecast_engine_strategy(self, smart_climate_entity):
        """Test integration with ForecastEngine active strategy."""
        # Arrange: ForecastEngine with active strategy
        mock_forecast_engine = Mock(spec=ForecastEngine)
        mock_forecast_engine.predictive_offset = 1.5
        mock_strategy_info = {
            "name": "heat_wave_precool",
            "adjustment": 1.5,
            "end_time": datetime.now().isoformat()
        }
        mock_forecast_engine.active_strategy_info = mock_strategy_info
        smart_climate_entity._forecast_engine = mock_forecast_engine
        smart_climate_entity._last_offset = 0.5
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should properly integrate with existing forecast functionality
        assert attributes["weather_forecast"] is True
        assert attributes["predictive_offset"] == 1.5
        assert attributes["total_offset"] == 2.0  # 0.5 + 1.5
        assert attributes["predictive_strategy"]["name"] == "heat_wave_precool"

    def test_graceful_degradation_with_errors(self, smart_climate_entity):
        """Test graceful degradation when multiple components have errors."""
        # Arrange: All components that could raise errors
        mock_delay_learner = Mock(spec=DelayLearner)
        mock_delay_learner.get_adaptive_delay.side_effect = RuntimeError("Delay error")
        smart_climate_entity._delay_learner = mock_delay_learner
        
        mock_forecast_engine = Mock(spec=ForecastEngine)
        # Need to use PropertyMock for property mocks
        type(mock_forecast_engine).predictive_offset = property(Mock(side_effect=ValueError("Forecast error")))
        type(mock_forecast_engine).active_strategy_info = property(Mock(side_effect=ValueError("Forecast error")))
        smart_climate_entity._forecast_engine = mock_forecast_engine
        
        mock_seasonal_learner = Mock()
        mock_seasonal_learner.get_seasonal_contribution.side_effect = AttributeError("Seasonal error")
        smart_climate_entity._offset_engine._seasonal_learner = mock_seasonal_learner
        
        # Act: Get attributes (should not raise exceptions)
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should provide safe defaults for all attributes
        assert attributes["adaptive_delay"] is None
        assert attributes["weather_forecast"] is True  # Because forecast_engine exists
        assert attributes["seasonal_adaptation"] is True  # Because seasonal_learner exists
        assert attributes["seasonal_contribution"] == 0
        
        # Should still have basic attributes
        assert "reactive_offset" in attributes
        assert "total_offset" in attributes

    def test_integration_with_existing_offset_engine_attributes(self, smart_climate_entity):
        """Test integration with existing OffsetEngine attributes."""
        # Arrange: Configure offset engine with learning state
        smart_climate_entity._offset_engine.get_learning_state = Mock(return_value={
            "is_learning": True,
            "sample_count": 150,
            "confidence": 0.85
        })
        smart_climate_entity._last_offset = 1.2
        
        # Act: Get attributes
        attributes = smart_climate_entity.extra_state_attributes
        
        # Assert: Should include both existing and new attributes
        assert "reactive_offset" in attributes
        assert attributes["reactive_offset"] == 1.2
        assert "adaptive_delay" in attributes
        assert "weather_forecast" in attributes
        assert "seasonal_adaptation" in attributes  
        assert "seasonal_contribution" in attributes