"""ABOUTME: Tests for seasonal intelligence expansion attributes in Smart Climate Entity.
Tests adding seasonal learning attributes (pattern count, outdoor temp bucket, seasonal accuracy) for dashboard visualization."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import OffsetInput, OffsetResult
from custom_components.smart_climate.seasonal_learner import LearnedPattern, SeasonalHysteresisLearner

# Import constants
from custom_components.smart_climate.const import DOMAIN


class TestSeasonalIntelligenceExpansion:
    """Tests for seasonal intelligence attributes in climate entity."""
    
    @pytest.fixture
    def hass_mock(self):
        """Create mock Home Assistant."""
        hass = Mock()
        hass.states = Mock()
        hass.services = Mock()
        hass.async_create_task = Mock()
        return hass
    
    @pytest.fixture
    def config_with_outdoor_sensor(self):
        """Configuration with outdoor sensor."""
        return {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "outdoor_sensor": "sensor.outdoor_temp",
            "power_sensor": "sensor.ac_power",
            "name": "Test Smart Climate",
            "max_offset": 5.0,
            "ml_enabled": True,
            "update_interval": 180,
            "default_target_temperature": 24.0
        }
    
    @pytest.fixture
    def config_without_outdoor_sensor(self):
        """Configuration without outdoor sensor."""
        return {
            "climate_entity": "climate.test_ac",
            "room_sensor": "sensor.room_temp",
            "name": "Test Smart Climate",
            "max_offset": 5.0,
            "ml_enabled": True,
            "update_interval": 180,
            "default_target_temperature": 24.0
        }
    
    @pytest.fixture
    def mock_seasonal_learner(self):
        """Create mock seasonal learner with test data."""
        learner = Mock(spec=SeasonalHysteresisLearner)
        
        # Create test patterns with different outdoor temperatures
        test_patterns = [
            LearnedPattern(timestamp=time.time() - 3600, start_temp=26.0, stop_temp=23.5, outdoor_temp=30.0),
            LearnedPattern(timestamp=time.time() - 7200, start_temp=25.5, stop_temp=23.0, outdoor_temp=32.0),
            LearnedPattern(timestamp=time.time() - 10800, start_temp=25.0, stop_temp=22.5, outdoor_temp=28.0),
            LearnedPattern(timestamp=time.time() - 14400, start_temp=24.5, stop_temp=22.0, outdoor_temp=25.0),
            LearnedPattern(timestamp=time.time() - 18000, start_temp=24.0, stop_temp=21.5, outdoor_temp=20.0),
        ]
        
        learner._patterns = test_patterns
        learner.get_relevant_hysteresis_delta.return_value = 2.5
        learner._get_current_outdoor_temp.return_value = 28.0
        
        return learner
    
    @pytest.fixture
    def mock_offset_engine_with_seasonal(self, mock_seasonal_learner):
        """Create mock offset engine with seasonal learning."""
        engine = Mock()
        engine._seasonal_learner = mock_seasonal_learner
        engine.calculate_offset.return_value = OffsetResult(
            offset=2.0, clamped=False, reason="seasonal-enhanced", confidence=0.85
        )
        return engine
    
    @pytest.fixture
    def mock_offset_engine_without_seasonal(self):
        """Create mock offset engine without seasonal learning."""
        engine = Mock()
        engine._seasonal_learner = None
        engine.calculate_offset.return_value = OffsetResult(
            offset=1.5, clamped=False, reason="basic", confidence=0.70
        )
        return engine
    
    @pytest.fixture
    def mock_sensor_manager(self):
        """Create mock sensor manager."""
        manager = Mock()
        manager.get_room_temperature.return_value = 24.5
        manager.get_outdoor_temperature.return_value = 28.0
        manager.get_power_consumption.return_value = 850.0
        manager.start_listening = Mock()
        manager.stop_listening = Mock()
        return manager
    
    @pytest.fixture
    def mock_mode_manager(self):
        """Create mock mode manager."""
        manager = Mock()
        manager.current_mode = "none"
        return manager
    
    @pytest.fixture
    def mock_temperature_controller(self):
        """Create mock temperature controller."""
        controller = Mock()
        controller.send_temperature_command = Mock()
        return controller
    
    @pytest.fixture
    def mock_coordinator(self):
        """Create mock coordinator."""
        coordinator = Mock()
        coordinator.async_add_listener = Mock()
        coordinator.async_config_entry_first_refresh = Mock()
        coordinator.async_force_startup_refresh = Mock()
        coordinator.data = None
        return coordinator
    
    def test_seasonal_pattern_count_with_seasonal_learner(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test seasonal_pattern_count returns correct count when seasonal learner exists."""
        # Create entity with seasonal learning
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp", 
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get attributes
        attributes = entity.extra_state_attributes
        
        # Should have 5 seasonal patterns from mock data
        assert "seasonal_pattern_count" in attributes
        assert attributes["seasonal_pattern_count"] == 5
    
    def test_seasonal_pattern_count_without_seasonal_learner(
        self, hass_mock, config_without_outdoor_sensor, mock_offset_engine_without_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test seasonal_pattern_count returns 0 when no seasonal learner."""
        # Create entity without seasonal learning
        entity = SmartClimateEntity(
            hass_mock,
            config_without_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_without_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get attributes
        attributes = entity.extra_state_attributes
        
        # Should have 0 patterns when no seasonal learner
        assert "seasonal_pattern_count" in attributes
        assert attributes["seasonal_pattern_count"] == 0
    
    def test_outdoor_temp_bucket_calculation(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test outdoor_temp_bucket calculation for different temperatures."""
        # Create entity with seasonal learning
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Test bucket calculation for 28.0°C (should be "25-30°C")
        attributes = entity.extra_state_attributes
        assert "outdoor_temp_bucket" in attributes
        assert attributes["outdoor_temp_bucket"] == "25-30°C"
    
    def test_outdoor_temp_bucket_edge_cases(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test outdoor temperature bucket calculation for edge cases."""
        # Create entity
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Test different outdoor temperatures
        test_cases = [
            (22.3, "20-25°C"),  # Mid bucket
            (25.0, "25-30°C"),  # Exact bucket boundary  
            (19.9, "15-20°C"),  # Just below boundary
            (30.0, "30-35°C"),  # Exact upper boundary
            (-5.2, "-10--5°C"), # Negative temperatures
            (0.0, "0-5°C"),     # Zero temperature
        ]
        
        for outdoor_temp, expected_bucket in test_cases:
            mock_sensor_manager.get_outdoor_temperature.return_value = outdoor_temp
            attributes = entity.extra_state_attributes
            assert attributes["outdoor_temp_bucket"] == expected_bucket, f"Failed for {outdoor_temp}°C"
    
    def test_outdoor_temp_bucket_without_outdoor_sensor(
        self, hass_mock, config_without_outdoor_sensor, mock_offset_engine_without_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test outdoor_temp_bucket when no outdoor sensor configured."""
        # Mock sensor manager to return None for outdoor temperature
        mock_sensor_manager.get_outdoor_temperature.return_value = None
        
        # Create entity without outdoor sensor
        entity = SmartClimateEntity(
            hass_mock,
            config_without_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_without_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get attributes
        attributes = entity.extra_state_attributes
        
        # Should return "Unknown" when no outdoor temperature
        assert "outdoor_temp_bucket" in attributes
        assert attributes["outdoor_temp_bucket"] == "Unknown"
    
    def test_seasonal_accuracy_calculation(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test seasonal accuracy calculation based on pattern reliability."""
        # Create entity with seasonal learning
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get attributes
        attributes = entity.extra_state_attributes
        
        # Should calculate accuracy based on pattern count and diversity
        assert "seasonal_accuracy" in attributes
        assert isinstance(attributes["seasonal_accuracy"], float)
        assert 0.0 <= attributes["seasonal_accuracy"] <= 100.0
        
        # With 5 patterns spanning different outdoor temps, accuracy should be reasonable
        assert attributes["seasonal_accuracy"] >= 45.0  # At least 45% with good pattern diversity
    
    def test_seasonal_accuracy_without_patterns(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test seasonal accuracy when no patterns are available."""
        # Mock seasonal learner with no patterns
        mock_offset_engine_with_seasonal._seasonal_learner._patterns = []
        
        # Create entity
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get attributes
        attributes = entity.extra_state_attributes
        
        # Should return 0% accuracy with no patterns
        assert attributes["seasonal_accuracy"] == 0.0
    
    def test_seasonal_accuracy_without_seasonal_learner(
        self, hass_mock, config_without_outdoor_sensor, mock_offset_engine_without_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test seasonal accuracy returns 0 when no seasonal learner."""
        # Create entity without seasonal learning
        entity = SmartClimateEntity(
            hass_mock,
            config_without_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_without_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get attributes  
        attributes = entity.extra_state_attributes
        
        # Should return 0% accuracy without seasonal learner
        assert "seasonal_accuracy" in attributes
        assert attributes["seasonal_accuracy"] == 0.0
    
    def test_seasonal_accuracy_calculation_algorithm(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator,
        mock_seasonal_learner
    ):
        """Test seasonal accuracy calculation algorithm with specific pattern scenarios."""
        # Test case 1: High diversity patterns (wide outdoor temp range)
        high_diversity_patterns = [
            LearnedPattern(timestamp=time.time() - 3600, start_temp=26.0, stop_temp=23.5, outdoor_temp=10.0),
            LearnedPattern(timestamp=time.time() - 7200, start_temp=25.5, stop_temp=23.0, outdoor_temp=20.0),
            LearnedPattern(timestamp=time.time() - 10800, start_temp=25.0, stop_temp=22.5, outdoor_temp=30.0),
            LearnedPattern(timestamp=time.time() - 14400, start_temp=24.5, stop_temp=22.0, outdoor_temp=40.0),
        ]
        mock_seasonal_learner._patterns = high_diversity_patterns
        
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        attributes = entity.extra_state_attributes
        high_diversity_accuracy = attributes["seasonal_accuracy"]
        
        # Test case 2: Low diversity patterns (narrow outdoor temp range)  
        low_diversity_patterns = [
            LearnedPattern(timestamp=time.time() - 3600, start_temp=26.0, stop_temp=23.5, outdoor_temp=25.0),
            LearnedPattern(timestamp=time.time() - 7200, start_temp=25.5, stop_temp=23.0, outdoor_temp=26.0),
            LearnedPattern(timestamp=time.time() - 10800, start_temp=25.0, stop_temp=22.5, outdoor_temp=24.0),
            LearnedPattern(timestamp=time.time() - 14400, start_temp=24.5, stop_temp=22.0, outdoor_temp=25.5),
        ]
        mock_seasonal_learner._patterns = low_diversity_patterns
        
        attributes = entity.extra_state_attributes
        low_diversity_accuracy = attributes["seasonal_accuracy"]
        
        # High diversity should result in higher accuracy than low diversity
        assert high_diversity_accuracy > low_diversity_accuracy
        assert high_diversity_accuracy >= 45.0  # Should be high with good diversity
        assert low_diversity_accuracy <= 40.0   # Should be lower with poor diversity
    
    def test_integration_with_existing_attributes(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test seasonal intelligence attributes integrate properly with existing attributes."""
        # Create entity
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get all attributes
        attributes = entity.extra_state_attributes
        
        # Verify seasonal intelligence attributes are present
        seasonal_attrs = ["seasonal_pattern_count", "outdoor_temp_bucket", "seasonal_accuracy"]
        for attr in seasonal_attrs:
            assert attr in attributes, f"Missing seasonal attribute: {attr}"
        
        # Verify existing attributes are still present
        existing_attrs = ["reactive_offset", "predictive_offset", "total_offset", "seasonal_adaptation"]
        for attr in existing_attrs:
            assert attr in attributes, f"Missing existing attribute: {attr}"
        
        # Verify attribute types
        assert isinstance(attributes["seasonal_pattern_count"], int)
        assert isinstance(attributes["outdoor_temp_bucket"], str)
        assert isinstance(attributes["seasonal_accuracy"], float)
    
    def test_error_handling_in_attribute_calculation(
        self, hass_mock, config_with_outdoor_sensor, mock_offset_engine_with_seasonal,
        mock_sensor_manager, mock_mode_manager, mock_temperature_controller, mock_coordinator
    ):
        """Test graceful error handling when calculating seasonal attributes."""
        # Mock seasonal learner to raise exception
        mock_offset_engine_with_seasonal._seasonal_learner._patterns = Mock(side_effect=Exception("Test error"))
        
        # Mock sensor manager to return None for outdoor temp to test that fallback
        mock_sensor_manager.get_outdoor_temperature.return_value = None
        
        # Create entity
        entity = SmartClimateEntity(
            hass_mock,
            config_with_outdoor_sensor,
            "climate.test_ac",
            "sensor.room_temp",
            mock_offset_engine_with_seasonal,
            mock_sensor_manager,
            mock_mode_manager,
            mock_temperature_controller,
            mock_coordinator
        )
        
        # Get attributes - should not raise exception
        attributes = entity.extra_state_attributes
        
        # Should have fallback values when errors occur
        assert "seasonal_pattern_count" in attributes
        assert "outdoor_temp_bucket" in attributes  
        assert "seasonal_accuracy" in attributes
        
        # Fallback values should be safe defaults
        assert attributes["seasonal_pattern_count"] == 0
        assert attributes["outdoor_temp_bucket"] == "Unknown"
        assert attributes["seasonal_accuracy"] == 0.0


class TestOutdoorTemperatureBucketHelper:
    """Tests for outdoor temperature bucket calculation helper functions."""
    
    def test_bucket_calculation_logic(self):
        """Test the bucket calculation logic directly."""
        # Test different temperatures and their expected buckets
        test_cases = [
            # Temperature, Expected Bucket
            (-15.0, "-15--10°C"),
            (-10.0, "-10--5°C"), 
            (-7.5, "-10--5°C"),
            (-5.0, "-5-0°C"),
            (-2.3, "-5-0°C"),
            (0.0, "0-5°C"),
            (2.5, "0-5°C"), 
            (5.0, "5-10°C"),
            (7.8, "5-10°C"),
            (10.0, "10-15°C"),
            (12.5, "10-15°C"),
            (15.0, "15-20°C"),
            (17.3, "15-20°C"),
            (20.0, "20-25°C"),
            (22.5, "20-25°C"),
            (25.0, "25-30°C"),
            (27.8, "25-30°C"),
            (30.0, "30-35°C"),
            (32.1, "30-35°C"),
            (35.0, "35-40°C"),
            (37.5, "35-40°C"),
            (40.0, "40-45°C"),
            (42.5, "40-45°C"),
            (45.0, "45-50°C"),
        ]
        
        for temp, expected_bucket in test_cases:
            # Calculate bucket using the same logic as implementation
            import math
            bucket_min = math.floor(temp / 5) * 5
            bucket_max = bucket_min + 5
            calculated_bucket = f"{bucket_min}-{bucket_max}°C"
            
            assert calculated_bucket == expected_bucket, \
                f"Temperature {temp}°C: expected {expected_bucket}, got {calculated_bucket}"


class TestSeasonalAccuracyCalculation:
    """Tests for seasonal accuracy calculation algorithms."""
    
    def test_accuracy_calculation_with_no_patterns(self):
        """Test accuracy is 0% with no learned patterns."""
        patterns = []
        accuracy = self._calculate_seasonal_accuracy(patterns)
        assert accuracy == 0.0
    
    def test_accuracy_calculation_with_single_pattern(self):
        """Test accuracy with only one pattern."""
        patterns = [
            LearnedPattern(timestamp=time.time(), start_temp=25.0, stop_temp=22.0, outdoor_temp=30.0)
        ]
        accuracy = self._calculate_seasonal_accuracy(patterns)
        
        # Single pattern should give low accuracy
        assert 0.0 <= accuracy <= 30.0
    
    def test_accuracy_calculation_with_high_diversity(self):
        """Test accuracy calculation with high outdoor temperature diversity."""
        patterns = [
            LearnedPattern(timestamp=time.time() - 3600, start_temp=26.0, stop_temp=23.0, outdoor_temp=5.0),
            LearnedPattern(timestamp=time.time() - 7200, start_temp=25.0, stop_temp=22.5, outdoor_temp=15.0),
            LearnedPattern(timestamp=time.time() - 10800, start_temp=24.5, stop_temp=22.0, outdoor_temp=25.0),
            LearnedPattern(timestamp=time.time() - 14400, start_temp=24.0, stop_temp=21.5, outdoor_temp=35.0),
            LearnedPattern(timestamp=time.time() - 18000, start_temp=23.5, stop_temp=21.0, outdoor_temp=45.0),
        ]
        accuracy = self._calculate_seasonal_accuracy(patterns)
        
        # High diversity across 40°C range should give good accuracy
        assert accuracy >= 55.0
    
    def test_accuracy_calculation_with_low_diversity(self):
        """Test accuracy calculation with low outdoor temperature diversity."""
        patterns = [
            LearnedPattern(timestamp=time.time() - 3600, start_temp=26.0, stop_temp=23.0, outdoor_temp=24.0),
            LearnedPattern(timestamp=time.time() - 7200, start_temp=25.5, stop_temp=22.8, outdoor_temp=25.0),
            LearnedPattern(timestamp=time.time() - 10800, start_temp=25.2, stop_temp=22.5, outdoor_temp=26.0),
            LearnedPattern(timestamp=time.time() - 14400, start_temp=25.0, stop_temp=22.2, outdoor_temp=24.5),
        ]
        accuracy = self._calculate_seasonal_accuracy(patterns)
        
        # Low diversity (2°C range) should give lower accuracy
        assert 30.0 <= accuracy <= 45.0
    
    def test_accuracy_calculation_with_recent_vs_old_patterns(self):
        """Test that recent patterns are weighted more heavily than old ones."""
        current_time = time.time()
        
        # Recent patterns with high diversity
        recent_patterns = [
            LearnedPattern(timestamp=current_time - 3600, start_temp=26.0, stop_temp=23.0, outdoor_temp=10.0),
            LearnedPattern(timestamp=current_time - 7200, start_temp=25.0, stop_temp=22.0, outdoor_temp=30.0),
            LearnedPattern(timestamp=current_time - 10800, start_temp=24.0, stop_temp=21.0, outdoor_temp=50.0),
        ]
        
        # Old patterns with high diversity (30+ days old)
        old_patterns = [
            LearnedPattern(timestamp=current_time - (35 * 24 * 3600), start_temp=26.0, stop_temp=23.0, outdoor_temp=10.0),
            LearnedPattern(timestamp=current_time - (36 * 24 * 3600), start_temp=25.0, stop_temp=22.0, outdoor_temp=30.0),
            LearnedPattern(timestamp=current_time - (37 * 24 * 3600), start_temp=24.0, stop_temp=21.0, outdoor_temp=50.0),
        ]
        
        recent_accuracy = self._calculate_seasonal_accuracy(recent_patterns)
        old_accuracy = self._calculate_seasonal_accuracy(old_patterns)
        
        # Recent patterns should have higher accuracy than old patterns
        assert recent_accuracy > old_accuracy
    
    def _calculate_seasonal_accuracy(self, patterns: list) -> float:
        """Helper method implementing the seasonal accuracy calculation algorithm.
        
        This mirrors the implementation logic that should be in the actual code.
        """
        if not patterns:
            return 0.0
        
        if len(patterns) == 1:
            return 20.0  # Single pattern gets low accuracy
        
        # Calculate outdoor temperature diversity
        outdoor_temps = [pattern.outdoor_temp for pattern in patterns]
        temp_range = max(outdoor_temps) - min(outdoor_temps)
        
        # Base accuracy from pattern count (more patterns = better)
        pattern_count_score = min(100.0, len(patterns) * 15)  # 15 points per pattern, max 100
        
        # Diversity bonus (wider temperature range = better seasonal coverage)
        diversity_score = min(50.0, temp_range * 2)  # 2 points per degree of range, max 50
        
        # Recency bonus (prefer recent patterns) 
        current_time = time.time()
        recent_patterns = [p for p in patterns if (current_time - p.timestamp) < (30 * 24 * 3600)]  # Last 30 days
        recency_score = (len(recent_patterns) / len(patterns)) * 20  # Max 20 point bonus
        
        # Combine scores
        total_score = pattern_count_score * 0.5 + diversity_score * 0.3 + recency_score * 0.2
        
        return min(100.0, total_score)