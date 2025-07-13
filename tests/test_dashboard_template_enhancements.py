"""
Test suite for Dashboard Template Enhancements (Issues #28 and #29).

Tests dashboard_generic.yaml template modifications for:
- Issue #28: Fix "Temperature & Offset History (24h)" chart
- Issue #29: Add new "System Overview" chart
"""
import pytest
import yaml
from pathlib import Path


class TestDashboardTemplateEnhancements:
    """Test dashboard template modifications for Issues #28 and #29."""

    @pytest.fixture
    def dashboard_template_path(self):
        """Path to dashboard template file."""
        return Path(__file__).parent.parent / "custom_components" / "smart_climate" / "dashboard" / "dashboard_generic.yaml"

    @pytest.fixture
    def dashboard_config(self, dashboard_template_path):
        """Load dashboard YAML configuration."""
        with open(dashboard_template_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def overview_view(self, dashboard_config):
        """Get the overview view from dashboard config."""
        return dashboard_config['views'][0]

    @pytest.fixture
    def performance_charts_section(self, overview_view):
        """Find the Performance Charts section."""
        for card in overview_view['cards']:
            if (card.get('type') == 'vertical-stack' and 
                len(card.get('cards', [])) > 0 and
                card['cards'][0].get('type') == 'markdown' and
                'Performance Charts' in card['cards'][0].get('content', '')):
                return card
        pytest.fail("Performance Charts section not found")

    def test_dashboard_yaml_loads_successfully(self, dashboard_template_path):
        """Test that dashboard YAML loads without syntax errors."""
        with open(dashboard_template_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert 'views' in config
        assert len(config['views']) > 0

    def test_performance_charts_section_exists(self, performance_charts_section):
        """Test that Performance Charts section exists and has expected structure."""
        assert performance_charts_section['type'] == 'vertical-stack'
        assert len(performance_charts_section['cards']) >= 3  # markdown + 2 charts minimum

    def test_temperature_offset_history_chart_exists(self, performance_charts_section):
        """Test that Temperature & Offset History chart exists."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        temp_offset_chart = None
        for chart in charts:
            if '24h' in chart.get('header', {}).get('title', ''):
                temp_offset_chart = chart
                break
        
        assert temp_offset_chart is not None
        assert 'Temperature & Offset History (24h)' in temp_offset_chart['header']['title']

    def test_issue_28_indoor_temperature_color_and_name(self, performance_charts_section):
        """Test Issue #28: Indoor temperature has cyan color and correct name."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        temp_offset_chart = None
        for chart in charts:
            if '24h' in chart.get('header', {}).get('title', ''):
                temp_offset_chart = chart
                break
        
        assert temp_offset_chart is not None
        
        # Find indoor temperature series
        indoor_temp_series = None
        for series in temp_offset_chart['series']:
            if series.get('entity') == 'REPLACE_ME_CLIMATE' and series.get('attribute') == 'current_temperature':
                indoor_temp_series = series
                break
        
        assert indoor_temp_series is not None
        assert indoor_temp_series['name'] == 'Indoor Temperature'
        assert indoor_temp_series['color'] == 'cyan'

    def test_issue_28_outdoor_temperature_added(self, performance_charts_section):
        """Test Issue #28: Outdoor temperature series added with blue color."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        temp_offset_chart = None
        for chart in charts:
            if '24h' in chart.get('header', {}).get('title', ''):
                temp_offset_chart = chart
                break
        
        assert temp_offset_chart is not None
        
        # Find outdoor temperature series
        outdoor_temp_series = None
        for series in temp_offset_chart['series']:
            if series.get('entity') == 'REPLACE_ME_OUTDOOR_SENSOR':
                outdoor_temp_series = series
                break
        
        assert outdoor_temp_series is not None
        assert outdoor_temp_series['name'] == 'Outdoor Temperature'
        assert outdoor_temp_series['color'] == 'blue'
        assert outdoor_temp_series['yaxis_id'] == 'temperature'

    def test_issue_28_applied_offset_unchanged(self, performance_charts_section):
        """Test Issue #28: Applied Offset series maintains red color."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        temp_offset_chart = None
        for chart in charts:
            if '24h' in chart.get('header', {}).get('title', ''):
                temp_offset_chart = chart
                break
        
        assert temp_offset_chart is not None
        
        # Find applied offset series
        offset_series = None
        for series in temp_offset_chart['series']:
            if series.get('entity') == 'REPLACE_ME_SENSOR_OFFSET':
                offset_series = series
                break
        
        assert offset_series is not None
        assert offset_series['name'] == 'Applied Offset'
        assert offset_series['color'] == 'red'

    def test_issue_28_prediction_accuracy_unchanged(self, performance_charts_section):
        """Test Issue #28: Prediction Accuracy series maintains green color."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        temp_offset_chart = None
        for chart in charts:
            if '24h' in chart.get('header', {}).get('title', ''):
                temp_offset_chart = chart
                break
        
        assert temp_offset_chart is not None
        
        # Find prediction accuracy series
        accuracy_series = None
        for series in temp_offset_chart['series']:
            if series.get('entity') == 'REPLACE_ME_SENSOR_ACCURACY':
                accuracy_series = series
                break
        
        assert accuracy_series is not None
        assert accuracy_series['name'] == 'Prediction Accuracy'
        assert accuracy_series['color'] == 'green'
        assert accuracy_series['yaxis_id'] == 'percentage'

    def test_issue_28_yaxis_configuration(self, performance_charts_section):
        """Test Issue #28: Y-axis configuration shows 0-100% for accuracy."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        temp_offset_chart = None
        for chart in charts:
            if '24h' in chart.get('header', {}).get('title', ''):
                temp_offset_chart = chart
                break
        
        assert temp_offset_chart is not None
        assert 'yaxis' in temp_offset_chart
        
        # Find percentage y-axis
        percentage_axis = None
        for axis in temp_offset_chart['yaxis']:
            if axis.get('id') == 'percentage':
                percentage_axis = axis
                break
        
        assert percentage_axis is not None
        assert percentage_axis.get('opposite') is True
        assert percentage_axis.get('decimals') == 0
        assert 'apex_config' in percentage_axis
        assert 'Accuracy (%)' in percentage_axis['apex_config']['title']['text']

    def test_issue_29_system_overview_chart_exists(self, performance_charts_section):
        """Test Issue #29: System Overview chart exists in Performance Charts section."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        system_overview_chart = None
        for chart in charts:
            if 'System Overview' in chart.get('header', {}).get('title', ''):
                system_overview_chart = chart
                break
        
        assert system_overview_chart is not None
        assert 'System Overview' in system_overview_chart['header']['title']

    def test_issue_29_indoor_temperature_series(self, performance_charts_section):
        """Test Issue #29: System Overview chart has Indoor Temperature series."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        system_overview_chart = None
        for chart in charts:
            if 'System Overview' in chart.get('header', {}).get('title', ''):
                system_overview_chart = chart
                break
        
        assert system_overview_chart is not None
        
        # Find indoor temperature series using room sensor
        indoor_temp_series = None
        for series in system_overview_chart['series']:
            if series.get('entity') == 'REPLACE_ME_ROOM_SENSOR':
                indoor_temp_series = series
                break
        
        assert indoor_temp_series is not None
        assert indoor_temp_series['name'] == 'Indoor Temperature'
        assert indoor_temp_series['yaxis_id'] == 'temperature'

    def test_issue_29_outdoor_temperature_series(self, performance_charts_section):
        """Test Issue #29: System Overview chart has conditional Outdoor Temperature series."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        system_overview_chart = None
        for chart in charts:
            if 'System Overview' in chart.get('header', {}).get('title', ''):
                system_overview_chart = chart
                break
        
        assert system_overview_chart is not None
        
        # Find outdoor temperature series
        outdoor_temp_series = None
        for series in system_overview_chart['series']:
            if series.get('entity') == 'REPLACE_ME_OUTDOOR_SENSOR':
                outdoor_temp_series = series
                break
        
        assert outdoor_temp_series is not None
        assert outdoor_temp_series['name'] == 'Outdoor Temperature'
        assert outdoor_temp_series['yaxis_id'] == 'temperature'

    def test_issue_29_set_temperature_series(self, performance_charts_section):
        """Test Issue #29: System Overview chart has Set Temperature series."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        system_overview_chart = None
        for chart in charts:
            if 'System Overview' in chart.get('header', {}).get('title', ''):
                system_overview_chart = chart
                break
        
        assert system_overview_chart is not None
        
        # Find set temperature series
        set_temp_series = None
        for series in system_overview_chart['series']:
            if (series.get('entity') == 'REPLACE_ME_CLIMATE' and 
                series.get('attribute') == 'temperature'):
                set_temp_series = series
                break
        
        assert set_temp_series is not None
        assert set_temp_series['name'] == 'Set Temperature'
        assert set_temp_series['yaxis_id'] == 'temperature'

    def test_issue_29_power_usage_series(self, performance_charts_section):
        """Test Issue #29: System Overview chart has conditional Power Usage series."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        system_overview_chart = None
        for chart in charts:
            if 'System Overview' in chart.get('header', {}).get('title', ''):
                system_overview_chart = chart
                break
        
        assert system_overview_chart is not None
        
        # Find power usage series
        power_series = None
        for series in system_overview_chart['series']:
            if series.get('entity') == 'REPLACE_ME_POWER_SENSOR':
                power_series = series
                break
        
        assert power_series is not None
        assert power_series['name'] == 'Power Usage'
        assert power_series['yaxis_id'] == 'power'

    def test_issue_29_yaxis_configuration(self, performance_charts_section):
        """Test Issue #29: System Overview chart has proper y-axis configuration."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        system_overview_chart = None
        for chart in charts:
            if 'System Overview' in chart.get('header', {}).get('title', ''):
                system_overview_chart = chart
                break
        
        assert system_overview_chart is not None
        assert 'yaxis' in system_overview_chart
        
        # Check temperature axis
        temp_axis = None
        power_axis = None
        for axis in system_overview_chart['yaxis']:
            if axis.get('id') == 'temperature':
                temp_axis = axis
            elif axis.get('id') == 'power':
                power_axis = axis
        
        assert temp_axis is not None
        assert 'Temperature (°C)' in temp_axis['apex_config']['title']['text']
        
        assert power_axis is not None
        assert power_axis.get('opposite') is True
        assert 'Power (W)' in power_axis['apex_config']['title']['text']

    def test_replace_me_placeholders_maintained(self, dashboard_config):
        """Test that all REPLACE_ME placeholders are maintained."""
        yaml_content = yaml.dump(dashboard_config, default_flow_style=False)
        
        # Check for key placeholders
        assert 'REPLACE_ME_CLIMATE' in yaml_content
        assert 'REPLACE_ME_ROOM_SENSOR' in yaml_content
        assert 'REPLACE_ME_OUTDOOR_SENSOR' in yaml_content
        assert 'REPLACE_ME_POWER_SENSOR' in yaml_content
        assert 'REPLACE_ME_SENSOR_OFFSET' in yaml_content
        assert 'REPLACE_ME_SENSOR_ACCURACY' in yaml_content

    def test_chart_structure_integrity(self, performance_charts_section):
        """Test that chart modifications don't break existing structure."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        # Should have at least 3 charts (existing 2 + new System Overview)
        assert len(charts) >= 3
        
        # Each chart should have required structure
        for chart in charts:
            assert 'header' in chart
            assert 'show' in chart['header']
            assert 'title' in chart['header']
            assert 'series' in chart
            assert len(chart['series']) > 0
            # Only charts with multiple y-axes need yaxis section
            if 'System Overview' in chart['header']['title'] or '24h' in chart['header']['title']:
                assert 'yaxis' in chart

    def test_conditional_sensor_handling(self, dashboard_config):
        """Test that conditional sensors are properly handled."""
        yaml_content = yaml.dump(dashboard_config, default_flow_style=False)
        
        # Outdoor and power sensors should be optional placeholders
        # They should be present but the dashboard service will handle
        # replacing them with actual entities or removing them
        assert 'REPLACE_ME_OUTDOOR_SENSOR' in yaml_content
        assert 'REPLACE_ME_POWER_SENSOR' in yaml_content

    def test_existing_charts_not_broken(self, performance_charts_section):
        """Test that existing charts are not broken by new modifications."""
        charts = [card for card in performance_charts_section['cards'] 
                 if card.get('type') == 'custom:apexcharts-card']
        
        # Find Learning Progress chart (should still exist)
        learning_chart = None
        for chart in charts:
            if '7 days' in chart.get('header', {}).get('title', '') and 'Learning Progress' in chart.get('header', {}).get('title', ''):
                learning_chart = chart
                break
        
        assert learning_chart is not None
        assert learning_chart['graph_span'] == '7d'
        assert len(learning_chart['series']) >= 2  # Learning Progress + Current Accuracy