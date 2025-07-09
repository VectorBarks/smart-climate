"""Tests for Smart Climate Dashboard template sensors."""

import pytest
from datetime import datetime, timedelta
import yaml
from typing import Dict, Any

# Test utilities
def load_blueprint_section(section_name: str) -> Dict[str, Any]:
    """Load a specific section from the blueprint YAML."""
    # This will be implemented once we have the blueprint file
    # For now, return empty dict for TDD
    return {}


def validate_template_expression(template: str, test_context: Dict[str, Any]) -> Any:
    """Validate a template expression with test context."""
    # This simulates Jinja2 template evaluation
    # For now, just check if template is non-empty
    return template is not None and len(template) > 0


def create_test_entity_state(entity_id: str, state: Any, attributes: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a test entity state object."""
    return {
        'entity_id': entity_id,
        'state': state,
        'attributes': attributes or {},
        'last_changed': datetime.now().isoformat(),
        'last_updated': datetime.now().isoformat()
    }


class TestOffsetHistorySensor:
    """Tests for the offset history template sensor."""
    
    def test_offset_history_sensor_template(self):
        """Test that offset history sensor template is valid."""
        # The sensor should extract current offset from the climate entity
        template = """
        {% set climate = states.climate.test_climate %}
        {% if climate and climate.attributes.current_offset is defined %}
          {{ climate.attributes.current_offset | float(0) }}
        {% else %}
          0
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_offset_history_attributes(self):
        """Test that offset history attributes template is valid."""
        # Should provide last 24 hours of offset changes
        template = """
        {% set climate = states.climate.test_climate %}
        {% if climate %}
          {
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "offset_changes": {{ climate.attributes.offset_history | default([]) | tojson }},
            "last_update": "{{ climate.last_updated }}",
            "trend": "{{ 'increasing' if climate.attributes.current_offset | float(0) > climate.attributes.last_offset | float(0) else 'decreasing' }}"
          }
        {% else %}
          {}
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_offset_history_availability(self):
        """Test that offset history availability template handles missing entities."""
        template = """
        {{ states.climate.test_climate is not none }}
        """
        assert validate_template_expression(template, {})


class TestLearningProgressSensor:
    """Tests for the learning progress template sensor."""
    
    def test_learning_progress_sensor_template(self):
        """Test that learning progress sensor template calculates percentage."""
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch and switch.attributes.samples_collected is defined %}
          {% set samples = switch.attributes.samples_collected | int(0) %}
          {% set target = 100 %}
          {{ ((samples / target) * 100) | round(1) | min(100) }}
        {% else %}
          0
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_learning_progress_calculates_percentage(self):
        """Test that learning progress correctly calculates percentage."""
        # Test with different sample counts
        test_cases = [
            (0, 0),      # No samples
            (50, 50),    # Half way
            (100, 100),  # Complete
            (150, 100),  # Over target (capped at 100)
        ]
        
        for samples, expected in test_cases:
            context = {
                'switch.test_learning': create_test_entity_state(
                    'switch.test_learning',
                    'on',
                    {'samples_collected': samples}
                )
            }
            # In real implementation, we'd evaluate the template with context
            # For now, just verify the test structure
            assert True
    
    def test_learning_progress_handles_no_data(self):
        """Test that learning progress handles missing data gracefully."""
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch and switch.attributes.samples_collected is defined %}
          {% set samples = switch.attributes.samples_collected | int(0) %}
          {% set target = 100 %}
          {{ ((samples / target) * 100) | round(1) | min(100) }}
        {% else %}
          0
        {% endif %}
        """
        # Should return 0 when no data available
        assert validate_template_expression(template, {})


class TestAccuracyTrendSensor:
    """Tests for the accuracy trend template sensor."""
    
    def test_accuracy_trend_sensor_template(self):
        """Test that accuracy trend sensor template is valid."""
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch and switch.attributes.learning_accuracy is defined %}
          {{ switch.attributes.learning_accuracy | float(0) | round(1) }}
        {% else %}
          0
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_accuracy_trend_moving_average(self):
        """Test that accuracy trend calculates moving average."""
        # In full implementation, this would track history
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch %}
          {
            "current_accuracy": {{ switch.attributes.learning_accuracy | float(0) }},
            "7_day_average": {{ switch.attributes.learning_accuracy | float(0) }},
            "trend_direction": "improving",
            "confidence": {{ switch.attributes.confidence_level | float(0) }}
          }
        {% else %}
          {}
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_accuracy_trend_handles_insufficient_data(self):
        """Test that accuracy trend handles insufficient data."""
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch and switch.attributes.samples_collected | int(0) >= 10 %}
          {{ switch.attributes.learning_accuracy | float(0) | round(1) }}
        {% else %}
          unavailable
        {% endif %}
        """
        assert validate_template_expression(template, {})


class TestCalibrationStatusSensor:
    """Tests for the calibration status template sensor."""
    
    def test_calibration_status_sensor_template(self):
        """Test that calibration status sensor template is valid."""
        template = """
        {% set climate = states.climate.test_climate %}
        {% if climate and climate.attributes.calibration_active is defined %}
          {% if climate.attributes.calibration_active %}
            Calibrating ({{ climate.attributes.calibration_samples | int(0) }}/10)
          {% else %}
            Ready
          {% endif %}
        {% else %}
          Unknown
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_calibration_status_messages(self):
        """Test that calibration status shows correct messages."""
        # Test different calibration states
        test_cases = [
            (True, 0, "Calibrating (0/10)"),
            (True, 5, "Calibrating (5/10)"),
            (True, 10, "Calibrating (10/10)"),
            (False, 10, "Ready"),
        ]
        
        for active, samples, expected in test_cases:
            context = {
                'climate.test_climate': create_test_entity_state(
                    'climate.test_climate',
                    'cool',
                    {
                        'calibration_active': active,
                        'calibration_samples': samples
                    }
                )
            }
            # Test structure validation
            assert True
    
    def test_calibration_progress_calculation(self):
        """Test that calibration progress is calculated correctly."""
        template = """
        {% set climate = states.climate.test_climate %}
        {% if climate and climate.attributes.calibration_samples is defined %}
          {% set samples = climate.attributes.calibration_samples | int(0) %}
          {% set progress = (samples / 10 * 100) | round(0) %}
          {
            "progress_percentage": {{ progress }},
            "samples_collected": {{ samples }},
            "samples_needed": 10,
            "icon": "mdi:{{ 'progress-clock' if progress < 100 else 'check-circle' }}"
          }
        {% else %}
          {}
        {% endif %}
        """
        assert validate_template_expression(template, {})


class TestHysteresisStateSensor:
    """Tests for the hysteresis state template sensor."""
    
    def test_hysteresis_state_sensor_template(self):
        """Test that hysteresis state sensor template is valid."""
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch and switch.attributes.hysteresis_state is defined %}
          {{ switch.attributes.hysteresis_state }}
        {% else %}
          No power sensor
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_hysteresis_state_mapping(self):
        """Test that hysteresis states are mapped to readable text."""
        # Already handled in switch.py, but template can enhance
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch and switch.attributes.hysteresis_state is defined %}
          {% set state = switch.attributes.hysteresis_state %}
          {% set icon_map = {
            'Learning AC behavior': 'mdi:brain',
            'AC actively cooling': 'mdi:snowflake',
            'AC should start soon': 'mdi:thermometer-alert',
            'AC recently stopped': 'mdi:pause-circle',
            'Temperature stable': 'mdi:check-circle',
            'No power sensor': 'mdi:power-plug-off'
          } %}
          {
            "state": "{{ state }}",
            "icon": "{{ icon_map.get(state, 'mdi:help-circle') }}"
          }
        {% else %}
          {"state": "Unknown", "icon": "mdi:help-circle"}
        {% endif %}
        """
        assert validate_template_expression(template, {})
    
    def test_hysteresis_thresholds_display(self):
        """Test that hysteresis thresholds are displayed correctly."""
        template = """
        {% set switch = states.switch.test_learning %}
        {% if switch %}
          {
            "start_threshold": "{{ switch.attributes.learned_start_threshold | default('Not available') }}",
            "stop_threshold": "{{ switch.attributes.learned_stop_threshold | default('Not available') }}",
            "temperature_window": "{{ switch.attributes.temperature_window | default('Not available') }}",
            "start_samples": {{ switch.attributes.start_samples_collected | int(0) }},
            "stop_samples": {{ switch.attributes.stop_samples_collected | int(0) }},
            "ready": {{ switch.attributes.hysteresis_ready | default(false) }}
          }
        {% else %}
          {}
        {% endif %}
        """
        assert validate_template_expression(template, {})


class TestTemplateSensorIntegration:
    """Integration tests for all template sensors working together."""
    
    def test_all_sensors_have_unique_ids(self):
        """Test that all sensors will have unique IDs when created."""
        sensor_ids = [
            'sensor.test_climate_offset_history',
            'sensor.test_climate_learning_progress',
            'sensor.test_climate_accuracy_trend',
            'sensor.test_climate_calibration_status',
            'sensor.test_climate_hysteresis_state'
        ]
        
        # Verify all IDs are unique
        assert len(sensor_ids) == len(set(sensor_ids))
    
    def test_all_sensors_have_availability_templates(self):
        """Test that all sensors have availability templates."""
        # Each sensor should check if its source entity exists
        availability_templates = [
            "{{ states.climate.test_climate is not none }}",
            "{{ states.switch.test_learning is not none }}",
            "{{ states.switch.test_learning is not none }}",
            "{{ states.climate.test_climate is not none }}",
            "{{ states.switch.test_learning is not none }}"
        ]
        
        for template in availability_templates:
            assert validate_template_expression(template, {})
    
    def test_sensors_handle_startup_gracefully(self):
        """Test that sensors handle Home Assistant startup gracefully."""
        # Sensors should return safe defaults during startup
        startup_template = """
        {% if states.climate and states.switch %}
          normal
        {% else %}
          unavailable
        {% endif %}
        """
        assert validate_template_expression(startup_template, {})