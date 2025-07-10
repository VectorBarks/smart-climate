"""Test fixtures for dashboard YAML validation."""
# ABOUTME: Provides test fixtures and sample data for dashboard YAML validation tests
# Used to test removal of deprecated span properties from ApexCharts cards

import pytest
from pathlib import Path


@pytest.fixture
def sample_dashboard_with_apex_span():
    """Sample dashboard YAML with deprecated span properties in ApexCharts cards."""
    return """title: Smart Climate - Test
views:
  - title: Overview
    path: overview
    cards:
      - type: custom:apexcharts-card
        header:
          show: true
          title: Temperature History
        graph_span: 24h
        span:
          end: day
        series:
          - entity: sensor.test_temperature
            name: Temperature
      - type: custom:apexcharts-card
        header:
          show: true
          title: Learning Progress
        graph_span: 7d
        span:
          end: day
        update_interval: 5min
        series:
          - entity: sensor.test_progress
            name: Progress
      - type: gauge
        entity: sensor.test_offset
        name: Current Offset
  - title: Stats
    path: stats
    cards:
      - type: custom:apexcharts-card
        header:
          show: true
          title: Detailed Metrics
        graph_span: 7d
        span:
          end: day
        series:
          - entity: sensor.test_accuracy
            name: Accuracy
"""


@pytest.fixture
def expected_dashboard_without_span():
    """Expected dashboard YAML with span properties removed from ApexCharts cards."""
    return """title: Smart Climate - Test
views:
  - title: Overview
    path: overview
    cards:
      - type: custom:apexcharts-card
        header:
          show: true
          title: Temperature History
        graph_span: 24h
        series:
          - entity: sensor.test_temperature
            name: Temperature
      - type: custom:apexcharts-card
        header:
          show: true
          title: Learning Progress
        graph_span: 7d
        update_interval: 5min
        series:
          - entity: sensor.test_progress
            name: Progress
      - type: gauge
        entity: sensor.test_offset
        name: Current Offset
  - title: Stats
    path: stats
    cards:
      - type: custom:apexcharts-card
        header:
          show: true
          title: Detailed Metrics
        graph_span: 7d
        series:
          - entity: sensor.test_accuracy
            name: Accuracy
"""


@pytest.fixture
def dashboard_with_placeholders():
    """Dashboard template with REPLACE_ME placeholders and apex span issues."""
    return """title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    path: overview
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
        name: Climate Control
      - type: custom:apexcharts-card
        header:
          show: true
          title: Temperature & Offset History (24h)
        graph_span: 24h
        span:
          end: day
        update_interval: 1min
        series:
          - entity: REPLACE_ME_CLIMATE
            attribute: current_temperature
            name: Current Temperature
          - entity: REPLACE_ME_SENSOR_OFFSET
            name: Applied Offset
      - type: custom:apexcharts-card
        header:
          show: true
          title: Learning Progress (7 days)
        graph_span: 7d
        span:
          end: day
        update_interval: 5min
        series:
          - entity: REPLACE_ME_SENSOR_PROGRESS
            name: Learning Progress
          - entity: REPLACE_ME_SENSOR_ACCURACY
            name: Current Accuracy
"""


@pytest.fixture
def dashboard_without_apex_cards():
    """Dashboard without any ApexCharts cards."""
    return """title: Smart Climate - Test
views:
  - title: Overview
    path: overview
    cards:
      - type: thermostat
        entity: climate.test_ac
        name: Climate Control
      - type: gauge
        entity: sensor.test_offset
        name: Current Offset
      - type: history-graph
        title: Temperature History
        entities:
          - entity: sensor.test_temperature
"""


@pytest.fixture
def dashboard_with_nested_cards():
    """Dashboard with ApexCharts cards nested in layout cards."""
    return """title: Smart Climate - Test
views:
  - title: Overview
    path: overview
    cards:
      - type: vertical-stack
        cards:
          - type: custom:apexcharts-card
            header:
              title: Nested Chart
            graph_span: 24h
            span:
              end: day
            series:
              - entity: sensor.test
          - type: horizontal-stack
            cards:
              - type: custom:apexcharts-card
                graph_span: 7d
                span:
                  end: week
                series:
                  - entity: sensor.test2
"""


@pytest.fixture
def dashboard_with_mixed_span_formats():
    """Dashboard with various span property formats."""
    return """title: Smart Climate - Test
views:
  - title: Overview
    cards:
      - type: custom:apexcharts-card
        graph_span: 24h
        span:
          end: day
        series:
          - entity: sensor.test1
      - type: custom:apexcharts-card
        graph_span: 48h
        span:
          start: day
          offset: -1d
        series:
          - entity: sensor.test2
      - type: custom:apexcharts-card
        graph_span: 7d
        span:
          end: week
          offset: +1d
        series:
          - entity: sensor.test3
"""


@pytest.fixture
def mock_dashboard_service_entities():
    """Mock entities for dashboard service testing."""
    return {
        "climate": "climate.living_room_ac",
        "sensors": {
            "offset_current": "sensor.living_room_ac_offset_current",
            "learning_progress": "sensor.living_room_ac_learning_progress",
            "accuracy_current": "sensor.living_room_ac_accuracy_current",
            "calibration_status": "sensor.living_room_ac_calibration_status",
            "hysteresis_state": "sensor.living_room_ac_hysteresis_state"
        },
        "switch": "switch.living_room_ac_learning",
        "button": "button.living_room_ac_reset_training_data"
    }


@pytest.fixture
def dashboard_with_invalid_yaml():
    """Dashboard with invalid YAML syntax."""
    return """title: Smart Climate - Test
views:
  - title: Overview
    cards:
      - type: custom:apexcharts-card
        graph_span: 24h
        span:
          end: day
        series: [invalid yaml here
          - entity: sensor.test
"""


@pytest.fixture
def dashboard_edge_cases():
    """Dashboard with edge cases for span removal."""
    return """title: Smart Climate - Test
views:
  - title: Overview
    cards:
      # ApexCharts with span in comment
      - type: custom:apexcharts-card
        graph_span: 24h
        span:  # This span should be removed
          end: day
        series:
          - entity: sensor.test1
      # Card with 'span' in the name
      - type: custom:apexcharts-card
        header:
          title: "Timespan Analysis"
        graph_span: 7d
        span:
          end: week
        series:
          - entity: sensor.spanning_data
      # Non-apex card with span property (should not be touched)
      - type: custom:other-card
        span: 24h
        entity: sensor.test
"""