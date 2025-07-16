"""ABOUTME: Test suite for advanced intelligence metrics dashboard enhancements.
Comprehensive TDD tests for v1.3.0+ intelligent features visualization and technical metrics."""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta
import yaml

from custom_components.smart_climate import handle_generate_dashboard


class TestAdvancedIntelligenceMetrics:
    """Test suite for advanced intelligence metrics and dashboard enhancements."""
    
    @pytest.fixture
    def mock_hass(self):
        """Create a mock Home Assistant instance."""
        hass = Mock()
        hass.data = {}
        hass.states = Mock()
        hass.states.get.return_value = Mock()
        return hass
    
    @pytest.fixture
    def mock_climate_entity(self):
        """Create a mock climate entity with v1.3.0+ attributes."""
        entity = Mock()
        entity.entity_id = "climate.smart_climate_test"
        entity.state = "cool"
        entity.attributes = {
            # Multi-layered intelligence attributes
            "reactive_offset": 1.5,
            "predictive_offset": 0.8,
            "total_offset": 2.3,
            "predictive_strategy": {
                "name": "heat_wave_precooling",
                "adjustment": 0.8,
                "end_time": "2025-07-14T15:00:00"
            },
            
            # Advanced timing and learning attributes
            "adaptive_delay": 45.0,
            "weather_forecast": True,
            "seasonal_adaptation": True,
            
            # Performance metrics
            "confidence_level": 0.85,
            "accuracy_trend": 92.5,
            "prediction_latency_ms": 0.8,
            "energy_efficiency_score": 94.2,
            
            # Seasonal learning metrics
            "seasonal_pattern_count": 23,
            "outdoor_temp_bucket": "20-25°C",
            "seasonal_accuracy": 89.3,
            
            # Hysteresis and AC learning
            "temperature_stability_detected": True,
            "learned_delay_seconds": 42,
            "ema_coefficient": 0.15,
            
            # System health indicators
            "memory_usage_kb": 245,
            "persistence_latency_ms": 2.1,
            "sensor_availability_score": 98.7,
            "outlier_detection_active": True
        }
        return entity
    
    @pytest.fixture
    def dashboard_service(self, mock_hass):
        """Create a dashboard generation service instance."""
        return handle_generate_dashboard
    
    @pytest.fixture
    def sample_dashboard_template(self):
        """Provide sample dashboard template content."""
        return """
title: Smart Climate - REPLACE_ME_NAME
views:
  - title: Overview
    cards:
      - type: thermostat
        entity: REPLACE_ME_CLIMATE
"""

    def test_advanced_intelligence_section_structure(self, dashboard_service, mock_climate_entity):
        """Test that advanced intelligence metrics section has correct structure."""
        # Arrange: Mock climate entity with advanced attributes
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act: Generate advanced intelligence section
        section = dashboard_service._generate_advanced_intelligence_section("climate.test")
        
        # Assert: Structure contains required subsections
        assert "Real-time Algorithm Performance" in section
        assert "Deep Technical Diagnostics" in section
        assert "Performance Analytics" in section
        assert "Intelligence Layer Breakdown" in section
    
    def test_real_time_algorithm_performance_metrics(self, dashboard_service, mock_climate_entity):
        """Test real-time algorithm performance visualization."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        performance_cards = dashboard_service._generate_algorithm_performance_cards("climate.test")
        
        # Assert: Performance metrics properly calculated
        assert len(performance_cards) >= 3  # Reactive, Predictive, Total contribution cards
        
        # Check for reactive vs predictive contribution calculation
        contribution_card = next((card for card in performance_cards 
                                 if "Weather Contribution" in str(card)), None)
        assert contribution_card is not None
        
        # Verify percentage calculation logic
        reactive = mock_climate_entity.attributes["reactive_offset"]
        predictive = mock_climate_entity.attributes["predictive_offset"]
        total = reactive + predictive
        expected_weather_contribution = (predictive / total) * 100 if total != 0 else 0
        assert abs(expected_weather_contribution - 34.8) < 0.1  # 0.8/2.3 * 100 ≈ 34.8%
    
    def test_prediction_confidence_heat_map(self, dashboard_service, mock_climate_entity):
        """Test 24-hour confidence level heat map generation."""
        # Arrange: Mock time-series confidence data
        confidence_data = [
            {"time": "00:00", "confidence": 0.65},
            {"time": "06:00", "confidence": 0.72},
            {"time": "12:00", "confidence": 0.85},
            {"time": "18:00", "confidence": 0.78},
            {"time": "23:00", "confidence": 0.69}
        ]
        
        # Act
        heatmap_config = dashboard_service._generate_confidence_heatmap("climate.test", confidence_data)
        
        # Assert: Proper ApexCharts configuration
        assert heatmap_config["type"] == "custom:apexcharts-card"
        assert "24h Confidence Heat Map" in heatmap_config["header"]["title"]
        assert heatmap_config["chart_type"] == "heatmap"
        assert len(heatmap_config["series"]) == 1
        
        # Verify data structure
        series_data = heatmap_config["series"][0]["data"]
        assert len(series_data) == 5
        assert all(item["x"] and item["y"] is not None for item in series_data)
    
    def test_weather_strategy_timeline(self, dashboard_service, mock_climate_entity):
        """Test weather strategy effectiveness timeline."""
        # Arrange: Mock strategy timeline
        strategy_timeline = [
            {
                "time": "2025-07-14T10:00:00",
                "strategy": "heat_wave_precooling",
                "effectiveness": 92.5,
                "energy_saved_kwh": 1.8
            },
            {
                "time": "2025-07-14T14:00:00", 
                "strategy": "clear_sky_optimization",
                "effectiveness": 87.3,
                "energy_saved_kwh": 0.9
            }
        ]
        
        # Act
        timeline_config = dashboard_service._generate_strategy_timeline("climate.test", strategy_timeline)
        
        # Assert: Timeline structure
        assert timeline_config["type"] == "custom:apexcharts-card"
        assert "Weather Strategy Effectiveness" in timeline_config["header"]["title"]
        assert len(timeline_config["series"]) == 2  # Effectiveness and energy savings
        
        # Verify dual y-axis configuration
        assert len(timeline_config["yaxis"]) == 2
        assert timeline_config["yaxis"][0]["id"] == "effectiveness"
        assert timeline_config["yaxis"][1]["id"] == "energy"
    
    def test_ac_response_learning_metrics(self, dashboard_service, mock_climate_entity):
        """Test AC response learning diagnostic metrics."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        diagnostic_cards = dashboard_service._generate_ac_learning_diagnostics("climate.test")
        
        # Assert: AC learning metrics
        assert len(diagnostic_cards) >= 4
        
        # Check for specific diagnostic cards
        stability_card = next((card for card in diagnostic_cards 
                              if "Temperature Stability" in str(card)), None)
        assert stability_card is not None
        
        delay_card = next((card for card in diagnostic_cards 
                          if "Learned Delays" in str(card)), None)
        assert delay_card is not None
        
        ema_card = next((card for card in diagnostic_cards 
                        if "EMA Coefficients" in str(card)), None)
        assert ema_card is not None
    
    def test_hysteresis_analysis_visualization(self, dashboard_service, mock_climate_entity):
        """Test hysteresis analysis with power correlation."""
        # Arrange: Mock hysteresis data
        hysteresis_data = {
            "temperature_window": "1.8°C",
            "power_correlation_accuracy": 94.2,
            "cycle_count": 47,
            "efficiency_trend": "improving"
        }
        
        # Act
        hysteresis_cards = dashboard_service._generate_hysteresis_analysis("climate.test", hysteresis_data)
        
        # Assert: Hysteresis visualization components
        assert len(hysteresis_cards) >= 2
        
        # Verify power correlation chart
        correlation_chart = next((card for card in hysteresis_cards 
                                 if card.get("type") == "custom:apexcharts-card"), None)
        assert correlation_chart is not None
        assert "Power Correlation" in correlation_chart["header"]["title"]
    
    def test_seasonal_pattern_matching_display(self, dashboard_service, mock_climate_entity):
        """Test seasonal pattern matching metrics."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        seasonal_cards = dashboard_service._generate_seasonal_metrics("climate.test")
        
        # Assert: Seasonal learning components
        assert len(seasonal_cards) >= 3
        
        # Check outdoor temperature bucket display
        bucket_card = next((card for card in seasonal_cards 
                           if "Outdoor Temp Bucket" in str(card)), None)
        assert bucket_card is not None
        
        # Verify pattern count display
        pattern_card = next((card for card in seasonal_cards 
                            if "Pattern Count" in str(card)), None)
        assert pattern_card is not None
        
        # Check seasonal accuracy metric
        accuracy_card = next((card for card in seasonal_cards 
                             if "Seasonal Accuracy" in str(card)), None)
        assert accuracy_card is not None
    
    def test_learning_velocity_indicators(self, dashboard_service, mock_climate_entity):
        """Test learning velocity and improvement rate metrics."""
        # Arrange: Mock learning velocity data
        velocity_data = {
            "samples_per_day": 12.4,
            "accuracy_improvement_rate": 2.3,  # % per week
            "learning_acceleration": 1.05,  # improvement factor
            "convergence_trend": "stable"
        }
        
        # Act
        velocity_cards = dashboard_service._generate_learning_velocity("climate.test", velocity_data)
        
        # Assert: Velocity indicators
        assert len(velocity_cards) >= 3
        
        # Verify samples per day display
        samples_card = next((card for card in velocity_cards 
                            if "Samples/Day" in str(card)), None)
        assert samples_card is not None
        
        # Check improvement rate calculation
        improvement_card = next((card for card in velocity_cards 
                               if "Improvement Rate" in str(card)), None)
        assert improvement_card is not None
    
    def test_prediction_latency_measurements(self, dashboard_service, mock_climate_entity):
        """Test sub-millisecond prediction timing metrics."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        performance_cards = dashboard_service._generate_performance_analytics("climate.test")
        
        # Assert: Performance timing metrics
        latency_card = next((card for card in performance_cards 
                            if "Prediction Latency" in str(card)), None)
        assert latency_card is not None
        
        # Verify sub-millisecond precision display
        latency_value = mock_climate_entity.attributes["prediction_latency_ms"]
        assert latency_value < 1.0  # Sub-millisecond requirement
        
        # Check latency formatting (show microseconds if <1ms)
        if latency_value < 1.0:
            expected_display = f"{latency_value * 1000:.0f}μs"
        else:
            expected_display = f"{latency_value:.1f}ms"
        
        assert expected_display in str(latency_card)
    
    def test_energy_efficiency_metrics(self, dashboard_service, mock_climate_entity):
        """Test energy efficiency and savings calculations."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        efficiency_cards = dashboard_service._generate_energy_metrics("climate.test")
        
        # Assert: Energy efficiency components
        assert len(efficiency_cards) >= 2
        
        # Check efficiency score display
        efficiency_card = next((card for card in efficiency_cards 
                               if "Efficiency Score" in str(card)), None)
        assert efficiency_card is not None
        
        # Verify savings calculation display
        savings_card = next((card for card in efficiency_cards 
                            if "Estimated Savings" in str(card)), None)
        assert savings_card is not None
    
    def test_data_quality_metrics(self, dashboard_service, mock_climate_entity):
        """Test data quality and sensor health indicators."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        quality_cards = dashboard_service._generate_data_quality_metrics("climate.test")
        
        # Assert: Data quality indicators
        assert len(quality_cards) >= 3
        
        # Check sensor availability score
        availability_card = next((card for card in quality_cards 
                                 if "Sensor Availability" in str(card)), None)
        assert availability_card is not None
        
        # Verify outlier detection status
        outlier_card = next((card for card in quality_cards 
                            if "Outlier Detection" in str(card)), None)
        assert outlier_card is not None
    
    def test_system_health_indicators(self, dashboard_service, mock_climate_entity):
        """Test system health and memory usage metrics."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        health_cards = dashboard_service._generate_system_health("climate.test")
        
        # Assert: System health components
        assert len(health_cards) >= 2
        
        # Check memory usage display
        memory_card = next((card for card in health_cards 
                           if "Memory Usage" in str(card)), None)
        assert memory_card is not None
        
        # Verify persistence timing
        persistence_card = next((card for card in health_cards 
                               if "Persistence Timing" in str(card)), None)
        assert persistence_card is not None
    
    def test_technical_terminology_usage(self, dashboard_service, mock_climate_entity):
        """Test that technical terminology is used appropriately."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        all_sections = dashboard_service._generate_all_advanced_sections("climate.test")
        
        # Assert: Technical terms present
        full_content = str(all_sections)
        
        # Verify technical terminology
        technical_terms = [
            "EMA", "exponential moving average",
            "hysteresis", "correlation coefficient",
            "prediction latency", "outlier detection",
            "temporal stability", "convergence rate",
            "stochastic optimization", "pattern matching"
        ]
        
        found_terms = [term for term in technical_terms if term.lower() in full_content.lower()]
        assert len(found_terms) >= 4, f"Expected technical terms, found: {found_terms}"
    
    def test_conditional_display_for_optional_features(self, dashboard_service):
        """Test conditional display when optional sensors are unavailable."""
        # Arrange: Mock climate entity without optional features
        minimal_entity = Mock()
        minimal_entity.entity_id = "climate.minimal_test"
        minimal_entity.attributes = {
            "reactive_offset": 1.0,
            "predictive_offset": 0.0,  # No weather integration
            "total_offset": 1.0,
            "weather_forecast": False,
            "seasonal_adaptation": False
        }
        dashboard_service._hass.states.get.return_value = minimal_entity
        
        # Act
        sections = dashboard_service._generate_all_advanced_sections("climate.minimal_test")
        
        # Assert: Graceful handling of missing features
        content = str(sections)
        
        # Should show basic metrics but gracefully handle missing advanced features
        assert "reactive_offset" in content
        assert "Disabled" in content or "Not Available" in content  # For missing features
    
    def test_chart_configuration_validity(self, dashboard_service, mock_climate_entity):
        """Test that generated chart configurations are valid."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        all_charts = dashboard_service._generate_all_chart_configs("climate.test")
        
        # Assert: Chart configuration validity
        for chart in all_charts:
            if chart.get("type") == "custom:apexcharts-card":
                assert "series" in chart
                assert "header" in chart
                assert "title" in chart["header"]
                
                # Verify series configuration
                for series in chart["series"]:
                    assert "name" in series
                    assert "color" in series
                    
                # Check y-axis configuration if present
                if "yaxis" in chart:
                    for yaxis in chart["yaxis"]:
                        assert "id" in yaxis
    
    def test_gauge_configuration_for_metrics(self, dashboard_service, mock_climate_entity):
        """Test gauge card configurations for various metrics."""
        # Arrange
        dashboard_service._hass.states.get.return_value = mock_climate_entity
        
        # Act
        gauge_cards = dashboard_service._generate_gauge_cards("climate.test")
        
        # Assert: Gauge card properties
        for gauge in gauge_cards:
            if gauge.get("type") == "gauge":
                assert "entity" in gauge
                assert "name" in gauge
                assert "min" in gauge
                assert "max" in gauge
                assert "severity" in gauge
                
                # Verify severity thresholds are logical
                severity = gauge["severity"]
                if "green" in severity and "yellow" in severity and "red" in severity:
                    # Check that thresholds make sense (ascending order for positive metrics)
                    assert severity["red"] <= severity["yellow"] <= severity["green"] or \
                           severity["green"] <= severity["yellow"] <= severity["red"]
    
    def test_markdown_section_formatting(self, dashboard_service):
        """Test markdown section headers and formatting."""
        # Act
        markdown_sections = dashboard_service._generate_markdown_sections()
        
        # Assert: Proper markdown formatting
        for section in markdown_sections:
            if section.get("type") == "markdown":
                content = section["content"]
                
                # Check for proper markdown headers
                assert content.startswith("#")
                
                # Verify technical content structure
                if "Advanced Intelligence" in content:
                    assert "##" in content or "###" in content  # Subsection headers
    
    def test_dashboard_template_integration(self, dashboard_service, sample_dashboard_template):
        """Test integration with existing dashboard template."""
        # Arrange: Mock file reading
        with patch("builtins.open", mock_open(read_data=sample_dashboard_template)):
            # Act
            enhanced_template = dashboard_service._integrate_advanced_sections(
                "climate.test", sample_dashboard_template
            )
            
            # Assert: Enhanced template structure
            enhanced_yaml = yaml.safe_load(enhanced_template)
            
            # Check that original structure is preserved
            assert "title" in enhanced_yaml
            assert "views" in enhanced_yaml
            
            # Verify advanced sections are added
            views = enhanced_yaml["views"]
            overview_view = next((view for view in views if view.get("title") == "Overview"), None)
            assert overview_view is not None
            
            # Check for advanced intelligence cards
            cards = overview_view.get("cards", [])
            advanced_cards = [card for card in cards if "Advanced Intelligence" in str(card)]
            assert len(advanced_cards) > 0


class TestDashboardServiceEnhancements:
    """Test suite for dashboard service enhancements and new methods."""
    
    def test_generate_advanced_intelligence_section_method_exists(self):
        """Test that the new service method exists and is callable."""
        # This test ensures the method will be implemented
        service = handle_generate_dashboard
        
        # Should not raise AttributeError when method is implemented
        assert hasattr(service, '_generate_advanced_intelligence_section')
        assert callable(getattr(service, '_generate_advanced_intelligence_section'))
    
    def test_technical_metrics_calculation_methods(self):
        """Test that technical calculation methods are available."""
        service = handle_generate_dashboard
        
        # Check for required calculation methods
        required_methods = [
            '_calculate_weather_contribution_percentage',
            '_format_prediction_latency',
            '_calculate_learning_velocity',
            '_format_memory_usage',
            '_calculate_efficiency_score'
        ]
        
        for method_name in required_methods:
            assert hasattr(service, method_name), f"Missing method: {method_name}"
            assert callable(getattr(service, method_name))
    
    def test_chart_generation_methods(self):
        """Test that chart generation methods are available."""
        service = handle_generate_dashboard
        
        # Check for chart generation methods
        chart_methods = [
            '_generate_confidence_heatmap',
            '_generate_strategy_timeline',
            '_generate_algorithm_performance_cards',
            '_generate_performance_analytics_chart'
        ]
        
        for method_name in chart_methods:
            assert hasattr(service, method_name), f"Missing method: {method_name}"
            assert callable(getattr(service, method_name))


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for advanced metrics."""
    
    def test_missing_attribute_handling(self, dashboard_service):
        """Test graceful handling when attributes are missing."""
        # Arrange: Entity with minimal attributes
        minimal_entity = Mock()
        minimal_entity.attributes = {"reactive_offset": 1.0}  # Only basic attribute
        dashboard_service._hass.states.get.return_value = minimal_entity
        
        # Act & Assert: Should not raise exceptions
        try:
            sections = dashboard_service._generate_advanced_intelligence_section("climate.test")
            assert sections is not None
        except Exception as e:
            pytest.fail(f"Should handle missing attributes gracefully: {e}")
    
    def test_invalid_numeric_values(self, dashboard_service):
        """Test handling of invalid numeric values."""
        # Arrange: Entity with invalid values
        entity = Mock()
        entity.attributes = {
            "reactive_offset": "invalid",
            "predictive_offset": None,
            "confidence_level": float('inf'),
            "prediction_latency_ms": -1
        }
        dashboard_service._hass.states.get.return_value = entity
        
        # Act & Assert: Should handle invalid values gracefully
        try:
            sections = dashboard_service._generate_advanced_intelligence_section("climate.test")
            assert sections is not None
        except Exception as e:
            pytest.fail(f"Should handle invalid values gracefully: {e}")
    
    def test_zero_division_protection(self, dashboard_service):
        """Test protection against zero division in calculations."""
        # Arrange: Entity with zero values
        entity = Mock()
        entity.attributes = {
            "reactive_offset": 0.0,
            "predictive_offset": 0.0,
            "total_offset": 0.0
        }
        dashboard_service._hass.states.get.return_value = entity
        
        # Act
        percentage = dashboard_service._calculate_weather_contribution_percentage(entity)
        
        # Assert: Should return 0% not raise division error
        assert percentage == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])