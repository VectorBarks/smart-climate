"""
ABOUTME: Comprehensive tests for dashboard constants module
ABOUTME: Tests color scheme, sensor mappings, refresh intervals, and card type constants
"""

import pytest
import re
from custom_components.smart_climate.dashboard.constants import (
    DashboardColors,
    SENSOR_MAPPINGS,
    REFRESH_INTERVALS,
    CARD_TYPES
)


class TestDashboardColors:
    """Test DashboardColors class provides valid color scheme."""

    def test_primary_colors_are_valid_hex(self):
        """Test that all primary colors are valid hex codes."""
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        
        assert hex_pattern.match(DashboardColors.PRIMARY), "PRIMARY color must be valid hex"
        assert hex_pattern.match(DashboardColors.PRIMARY_LIGHT), "PRIMARY_LIGHT color must be valid hex"
        assert hex_pattern.match(DashboardColors.SUCCESS), "SUCCESS color must be valid hex"
        assert hex_pattern.match(DashboardColors.WARNING), "WARNING color must be valid hex"
        assert hex_pattern.match(DashboardColors.ERROR), "ERROR color must be valid hex"
        assert hex_pattern.match(DashboardColors.NEUTRAL), "NEUTRAL color must be valid hex"

    def test_primary_color_values(self):
        """Test that primary colors match expected values from architecture."""
        assert DashboardColors.PRIMARY == '#1976D2'
        assert DashboardColors.PRIMARY_LIGHT == '#42A5F5'
        assert DashboardColors.SUCCESS == '#4CAF50'
        assert DashboardColors.WARNING == '#FFA726'
        assert DashboardColors.ERROR == '#EF5350'
        assert DashboardColors.NEUTRAL == '#9E9E9E'

    def test_series_colors_exist(self):
        """Test that SERIES_COLORS dictionary exists with expected keys."""
        expected_keys = {'setpoint', 'actual', 'outdoor', 'offset', 'prediction'}
        assert hasattr(DashboardColors, 'SERIES_COLORS'), "SERIES_COLORS must exist"
        assert set(DashboardColors.SERIES_COLORS.keys()) == expected_keys
        
    def test_series_colors_are_valid_hex(self):
        """Test that all series colors are valid hex codes."""
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        
        for key, color in DashboardColors.SERIES_COLORS.items():
            assert hex_pattern.match(color), f"Series color '{key}' must be valid hex: {color}"

    def test_series_color_values(self):
        """Test that series colors match expected values from architecture."""
        expected_values = {
            'setpoint': '#1976D2',
            'actual': '#4CAF50',
            'outdoor': '#FFA726',
            'offset': '#9C27B0',
            'prediction': '#00BCD4'
        }
        
        for key, expected_color in expected_values.items():
            actual_color = DashboardColors.SERIES_COLORS[key]
            assert actual_color == expected_color, f"Series color '{key}' should be {expected_color}, got {actual_color}"


class TestSensorMappings:
    """Test SENSOR_MAPPINGS dictionary provides correct sensor entity mappings."""

    def test_sensor_mappings_exist(self):
        """Test that SENSOR_MAPPINGS dictionary exists and is not empty."""
        assert SENSOR_MAPPINGS is not None, "SENSOR_MAPPINGS must not be None"
        assert len(SENSOR_MAPPINGS) > 0, "SENSOR_MAPPINGS must not be empty"

    def test_sensor_mappings_have_entity_placeholder(self):
        """Test that all sensor mappings contain {entity} placeholder."""
        for key, mapping in SENSOR_MAPPINGS.items():
            assert '{entity}' in mapping, f"Mapping '{key}' must contain {{entity}} placeholder: {mapping}"

    def test_sensor_mappings_format(self):
        """Test that all sensor mappings follow correct format pattern."""
        pattern = re.compile(r'^sensor\.{entity}_[a-z_]+$')
        
        for key, mapping in SENSOR_MAPPINGS.items():
            assert pattern.match(mapping), f"Mapping '{key}' must follow 'sensor.{{entity}}_suffix' format: {mapping}"

    def test_expected_sensor_mappings_exist(self):
        """Test that all expected sensor mappings from architecture are present."""
        expected_keys = {
            'offset_current',
            'learning_progress', 
            'confidence',
            'tau_cooling',
            'tau_warming',
            'thermal_state',
            'accuracy_current',
            'mae',
            'rmse',
            'last_update',
            'error_count',
            'cycle_health'
        }
        
        actual_keys = set(SENSOR_MAPPINGS.keys())
        assert actual_keys == expected_keys, f"Missing or extra keys: expected {expected_keys}, got {actual_keys}"

    def test_sensor_mapping_values(self):
        """Test that sensor mappings match expected values from architecture."""
        expected_mappings = {
            'offset_current': 'sensor.{entity}_offset_current',
            'learning_progress': 'sensor.{entity}_learning_progress',
            'confidence': 'sensor.{entity}_confidence',
            'tau_cooling': 'sensor.{entity}_tau_cooling',
            'tau_warming': 'sensor.{entity}_tau_warming',
            'thermal_state': 'sensor.{entity}_thermal_state',
            'accuracy_current': 'sensor.{entity}_accuracy_current',
            'mae': 'sensor.{entity}_mae',
            'rmse': 'sensor.{entity}_rmse',
            'last_update': 'sensor.{entity}_last_update',
            'error_count': 'sensor.{entity}_error_count',
            'cycle_health': 'sensor.{entity}_cycle_health'
        }
        
        for key, expected_mapping in expected_mappings.items():
            actual_mapping = SENSOR_MAPPINGS[key]
            assert actual_mapping == expected_mapping, f"Mapping '{key}' should be {expected_mapping}, got {actual_mapping}"

    def test_entity_replacement_works(self):
        """Test that entity placeholder can be replaced correctly."""
        test_entity = "living_room_ac"
        
        for key, mapping in SENSOR_MAPPINGS.items():
            result = mapping.format(entity=test_entity)
            expected = f"sensor.{test_entity}_{key}"
            assert result == expected, f"Replacement failed for '{key}': expected {expected}, got {result}"


class TestRefreshIntervals:
    """Test REFRESH_INTERVALS dictionary provides correct timing configurations."""

    def test_refresh_intervals_exist(self):
        """Test that REFRESH_INTERVALS dictionary exists and is not empty."""
        assert REFRESH_INTERVALS is not None, "REFRESH_INTERVALS must not be None"
        assert len(REFRESH_INTERVALS) > 0, "REFRESH_INTERVALS must not be empty"

    def test_refresh_intervals_are_positive_integers(self):
        """Test that all refresh intervals are positive integers."""
        for key, interval in REFRESH_INTERVALS.items():
            assert isinstance(interval, int), f"Interval '{key}' must be an integer: {interval}"
            assert interval > 0, f"Interval '{key}' must be positive: {interval}"

    def test_expected_refresh_intervals_exist(self):
        """Test that all expected refresh intervals from architecture are present."""
        expected_keys = {'real_time', 'recent', 'historical'}
        actual_keys = set(REFRESH_INTERVALS.keys())
        assert actual_keys == expected_keys, f"Missing or extra keys: expected {expected_keys}, got {actual_keys}"

    def test_refresh_interval_values(self):
        """Test that refresh intervals match expected values from architecture."""
        expected_intervals = {
            'real_time': 1,
            'recent': 30,
            'historical': 300
        }
        
        for key, expected_interval in expected_intervals.items():
            actual_interval = REFRESH_INTERVALS[key]
            assert actual_interval == expected_interval, f"Interval '{key}' should be {expected_interval}, got {actual_interval}"

    def test_refresh_intervals_order(self):
        """Test that refresh intervals are in ascending order (real_time < recent < historical)."""
        assert REFRESH_INTERVALS['real_time'] < REFRESH_INTERVALS['recent'], "real_time should be less than recent"
        assert REFRESH_INTERVALS['recent'] < REFRESH_INTERVALS['historical'], "recent should be less than historical"


class TestCardTypes:
    """Test CARD_TYPES constant provides expected card type definitions."""

    def test_card_types_exist(self):
        """Test that CARD_TYPES constant exists and is not empty."""
        assert CARD_TYPES is not None, "CARD_TYPES must not be None"
        assert len(CARD_TYPES) > 0, "CARD_TYPES must not be empty"

    def test_card_types_structure(self):
        """Test that CARD_TYPES has expected structure with core and custom categories."""
        assert 'core' in CARD_TYPES, "CARD_TYPES must have 'core' category"
        assert 'custom' in CARD_TYPES, "CARD_TYPES must have 'custom' category"
        
        assert isinstance(CARD_TYPES['core'], dict), "core card types must be a dictionary"
        assert isinstance(CARD_TYPES['custom'], dict), "custom card types must be a dictionary"

    def test_core_card_types(self):
        """Test that core card types include expected HA built-in cards."""
        expected_core_types = {
            'thermostat',
            'gauge', 
            'entities',
            'history_graph',
            'statistics_graph'
        }
        
        actual_core_types = set(CARD_TYPES['core'].keys())
        assert expected_core_types.issubset(actual_core_types), f"Missing core card types: {expected_core_types - actual_core_types}"

    def test_custom_card_types(self):
        """Test that custom card types include expected HACS cards."""
        expected_custom_types = {
            'apexcharts',
            'plotly_graph', 
            'mini_graph',
            'button'
        }
        
        actual_custom_types = set(CARD_TYPES['custom'].keys())
        assert expected_custom_types.issubset(actual_custom_types), f"Missing custom card types: {expected_custom_types - actual_custom_types}"

    def test_card_type_values_are_strings(self):
        """Test that all card type values are non-empty strings."""
        for category, card_types in CARD_TYPES.items():
            for card_key, card_type in card_types.items():
                assert isinstance(card_type, str), f"{category}.{card_key} must be a string: {card_type}"
                assert len(card_type.strip()) > 0, f"{category}.{card_key} must not be empty: {card_type}"

    def test_custom_card_type_prefixes(self):
        """Test that custom card types have 'custom:' prefix."""
        for card_key, card_type in CARD_TYPES['custom'].items():
            assert card_type.startswith('custom:'), f"Custom card '{card_key}' must start with 'custom:': {card_type}"


class TestModuleIntegration:
    """Test that all constants work together and can be imported properly."""

    def test_all_constants_importable(self):
        """Test that all expected constants can be imported from module."""
        # This test implicitly passes if the imports at the top work
        assert DashboardColors is not None
        assert SENSOR_MAPPINGS is not None 
        assert REFRESH_INTERVALS is not None
        assert CARD_TYPES is not None

    def test_constants_consistency(self):
        """Test that constants are consistent with each other."""
        # Colors used in series should exist in primary colors or be valid
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        
        for series_key, color in DashboardColors.SERIES_COLORS.items():
            assert hex_pattern.match(color), f"Series color '{series_key}' must be valid hex: {color}"
        
        # Sensor mappings should cover all expected dashboard needs
        critical_sensors = ['offset_current', 'confidence', 'thermal_state', 'cycle_health']
        for sensor in critical_sensors:
            assert sensor in SENSOR_MAPPINGS, f"Critical sensor '{sensor}' must be mapped"

    def test_no_circular_dependencies(self):
        """Test that constants module has no circular import dependencies."""
        # This test passes if the module can be imported without errors
        import custom_components.smart_climate.dashboard.constants
        assert hasattr(custom_components.smart_climate.dashboard.constants, 'DashboardColors')
        assert hasattr(custom_components.smart_climate.dashboard.constants, 'SENSOR_MAPPINGS')
        assert hasattr(custom_components.smart_climate.dashboard.constants, 'REFRESH_INTERVALS')
        assert hasattr(custom_components.smart_climate.dashboard.constants, 'CARD_TYPES')


if __name__ == "__main__":
    pytest.main([__file__])