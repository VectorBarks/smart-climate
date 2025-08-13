"""Tests for FeatureEngineering component."""

import pytest
import math
from datetime import time
from unittest.mock import Mock

from custom_components.smart_climate.feature_engineering import FeatureEngineering
from custom_components.smart_climate.models import OffsetInput


class TestFeatureEngineering:
    """Test suite for FeatureEngineering class."""

    @pytest.fixture
    def feature_engineer(self):
        """Create a FeatureEngineering instance for testing."""
        return FeatureEngineering()

    def test_calculate_dew_point_known_values_1(self, feature_engineer):
        """Test dew point calculation with known value: 25°C, 60% humidity."""
        # Expected: approximately 16.7°C using Magnus formula
        result = feature_engineer.calculate_dew_point(25.0, 60.0)
        assert result is not None
        assert abs(result - 16.7) < 0.1  # Allow small tolerance for rounding

    def test_calculate_dew_point_known_values_2(self, feature_engineer):
        """Test dew point calculation with known value: 30°C, 80% humidity."""
        # Expected: approximately 26.2°C using Magnus formula
        result = feature_engineer.calculate_dew_point(30.0, 80.0)
        assert result is not None
        assert abs(result - 26.2) < 0.1  # Allow small tolerance for rounding

    def test_calculate_dew_point_none_temperature(self, feature_engineer):
        """Test dew point calculation with None temperature."""
        result = feature_engineer.calculate_dew_point(None, 60.0)
        assert result is None

    def test_calculate_dew_point_none_humidity(self, feature_engineer):
        """Test dew point calculation with None humidity."""
        result = feature_engineer.calculate_dew_point(25.0, None)
        assert result is None

    def test_calculate_dew_point_both_none(self, feature_engineer):
        """Test dew point calculation with both parameters None."""
        result = feature_engineer.calculate_dew_point(None, None)
        assert result is None

    def test_calculate_heat_index_known_value_1(self, feature_engineer):
        """Test heat index calculation with known value: 30°C, 70% humidity."""
        # Expected: approximately 35.6°C using Steadman's formula
        result = feature_engineer.calculate_heat_index(30.0, 70.0)
        assert result is not None
        assert abs(result - 35.6) < 1.0  # Allow tolerance for heat index approximation

    def test_calculate_heat_index_too_cold(self, feature_engineer):
        """Test heat index calculation with temperature too cold (< 20°C)."""
        result = feature_engineer.calculate_heat_index(18.0, 50.0)
        assert result is None

    def test_calculate_heat_index_none_temperature(self, feature_engineer):
        """Test heat index calculation with None temperature."""
        result = feature_engineer.calculate_heat_index(None, 70.0)
        assert result is None

    def test_calculate_heat_index_none_humidity(self, feature_engineer):
        """Test heat index calculation with None humidity."""
        result = feature_engineer.calculate_heat_index(30.0, None)
        assert result is None

    def test_calculate_heat_index_both_none(self, feature_engineer):
        """Test heat index calculation with both parameters None."""
        result = feature_engineer.calculate_heat_index(None, None)
        assert result is None

    def test_enrich_features_full_data(self, feature_engineer):
        """Test enrich_features with complete humidity data."""
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=28.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=55.0,
            outdoor_humidity=45.0
        )
        
        result = feature_engineer.enrich_features(input_data)
        
        # Check humidity_differential calculation
        assert result.humidity_differential == 10.0  # 55 - 45
        
        # Check indoor_dew_point calculation (24°C, 55% humidity ≈ 14.8°C)
        assert result.indoor_dew_point is not None
        assert abs(result.indoor_dew_point - 14.8) < 0.5
        
        # Check outdoor_dew_point calculation (28°C, 45% humidity ≈ 15.3°C)  
        assert result.outdoor_dew_point is not None
        assert abs(result.outdoor_dew_point - 15.3) < 0.4
        
        # Check heat_index calculation (24°C, 55% humidity)
        assert result.heat_index is not None

    def test_enrich_features_only_indoor_humidity(self, feature_engineer):
        """Test enrich_features with only indoor humidity data."""
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=28.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=55.0,
            outdoor_humidity=None
        )
        
        result = feature_engineer.enrich_features(input_data)
        
        # No humidity_differential (outdoor missing)
        assert result.humidity_differential is None
        
        # Indoor dew point should be calculated
        assert result.indoor_dew_point is not None
        
        # No outdoor dew point (outdoor humidity missing)
        assert result.outdoor_dew_point is None
        
        # Heat index should be calculated with indoor data
        assert result.heat_index is not None

    def test_enrich_features_no_humidity_data(self, feature_engineer):
        """Test enrich_features with no humidity data."""
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=28.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=None,
            outdoor_humidity=None
        )
        
        result = feature_engineer.enrich_features(input_data)
        
        # All derived humidity features should be None
        assert result.humidity_differential is None
        assert result.indoor_dew_point is None
        assert result.outdoor_dew_point is None
        assert result.heat_index is None

    def test_enrich_features_preserves_original_fields(self, feature_engineer):
        """Test that enrich_features preserves all original OffsetInput fields."""
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=28.0,
            mode="cool",
            power_consumption=150.0,
            time_of_day=time(14, 30),
            day_of_week=1,
            indoor_humidity=55.0,
            outdoor_humidity=45.0
        )
        
        result = feature_engineer.enrich_features(input_data)
        
        # Verify all original fields are preserved
        assert result.ac_internal_temp == 22.0
        assert result.room_temp == 24.0
        assert result.outdoor_temp == 28.0
        assert result.mode == "cool"
        assert result.power_consumption == 150.0
        assert result.time_of_day == time(14, 30)
        assert result.day_of_week == 1
        assert result.indoor_humidity == 55.0
        assert result.outdoor_humidity == 45.0