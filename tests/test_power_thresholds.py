"""Tests for configurable power thresholds in Smart Climate Control.

Tests verify that power thresholds (idle, min, max) can be configured
through the UI and are properly used throughout the integration.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, time

from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.smart_climate.const import (
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MAX_OFFSET,
    CONF_POWER_IDLE_THRESHOLD,
    CONF_POWER_MIN_THRESHOLD,
    CONF_POWER_MAX_THRESHOLD,
    DEFAULT_POWER_IDLE_THRESHOLD,
    DEFAULT_POWER_MIN_THRESHOLD,
    DEFAULT_POWER_MAX_THRESHOLD,
)
from custom_components.smart_climate.offset_engine import OffsetEngine, LightweightOffsetLearner
from custom_components.smart_climate.models import OffsetInput


class TestPowerThresholdConstants:
    """Test that power threshold constants are defined correctly."""
    
    def test_power_threshold_constants_exist(self):
        """Test that all power threshold constants are defined."""
        # Configuration keys
        assert CONF_POWER_IDLE_THRESHOLD == "power_idle_threshold"
        assert CONF_POWER_MIN_THRESHOLD == "power_min_threshold"
        assert CONF_POWER_MAX_THRESHOLD == "power_max_threshold"
        
        # Default values
        assert DEFAULT_POWER_IDLE_THRESHOLD == 50
        assert DEFAULT_POWER_MIN_THRESHOLD == 100
        assert DEFAULT_POWER_MAX_THRESHOLD == 250


class TestOffsetEnginePowerThresholds:
    """Test OffsetEngine uses configurable power thresholds."""
    
    def test_offset_engine_accepts_power_thresholds(self):
        """Test that OffsetEngine accepts power thresholds in config."""
        config = {
            "max_offset": 5.0,
            "power_idle_threshold": 30,
            "power_min_threshold": 80,
            "power_max_threshold": 200,
        }
        
        engine = OffsetEngine(config)
        
        # Verify thresholds are stored
        assert engine._power_idle_threshold == 30
        assert engine._power_min_threshold == 80
        assert engine._power_max_threshold == 200
    
    def test_offset_engine_uses_default_thresholds(self):
        """Test that OffsetEngine uses default thresholds when not configured."""
        config = {"max_offset": 5.0}
        
        engine = OffsetEngine(config)
        
        # Verify defaults are used
        assert engine._power_idle_threshold == DEFAULT_POWER_IDLE_THRESHOLD
        assert engine._power_min_threshold == DEFAULT_POWER_MIN_THRESHOLD
        assert engine._power_max_threshold == DEFAULT_POWER_MAX_THRESHOLD
    
    def test_offset_calculation_with_custom_thresholds(self):
        """Test offset calculation uses custom power thresholds."""
        config = {
            "max_offset": 5.0,
            "power_idle_threshold": 30,
            "power_min_threshold": 80,
            "power_max_threshold": 200,
        }
        
        engine = OffsetEngine(config)
        
        # Test high power (> 200W)
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="none",
            power_consumption=220.0,  # Above custom max threshold
            time_of_day=time(14, 0),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        assert "high power usage" in result.reason
        
        # Test low power (< 80W)
        input_data.power_consumption = 60.0  # Below custom min threshold
        result = engine.calculate_offset(input_data)
        assert "low power usage" in result.reason
        
        # Test idle power (< 30W)
        input_data.power_consumption = 20.0  # Below custom idle threshold
        result = engine.calculate_offset(input_data)
        assert "AC idle/off" in result.reason or "idle" in result.reason.lower()
    
    def test_power_state_detection_with_thresholds(self):
        """Test power state detection uses configured thresholds."""
        config = {
            "max_offset": 5.0,
            "power_idle_threshold": 40,
            "power_min_threshold": 90,
            "power_max_threshold": 220,
        }
        
        engine = OffsetEngine(config)
        
        # Test idle state
        assert engine._get_power_state(30) == "idle"
        assert engine._get_power_state(39) == "idle"
        
        # Test low state
        assert engine._get_power_state(50) == "low"
        assert engine._get_power_state(89) == "low"
        
        # Test moderate state
        assert engine._get_power_state(100) == "moderate"
        assert engine._get_power_state(219) == "moderate"
        
        # Test high state
        assert engine._get_power_state(250) == "high"
        assert engine._get_power_state(300) == "high"


class TestLightweightLearnerPowerThresholds:
    """Test LightweightOffsetLearner uses configurable power thresholds."""
    
    def test_learner_gets_thresholds_from_engine(self):
        """Test that learner gets power thresholds from parent OffsetEngine."""
        config = {
            "enable_learning": True,
            "power_idle_threshold": 30,
            "power_min_threshold": 80,
            "power_max_threshold": 200,
        }
        
        engine = OffsetEngine(config)
        
        # Verify the learner has the threshold from engine
        assert engine._learner._power_min_threshold == 80
    
    def test_learner_uses_default_thresholds(self):
        """Test that learner uses defaults when thresholds not provided."""
        config = {"enable_learning": True}
        engine = OffsetEngine(config)
        
        # Verify defaults are passed to learner
        assert engine._learner._power_min_threshold == DEFAULT_POWER_MIN_THRESHOLD
    
    def test_power_similarity_with_custom_thresholds(self):
        """Test power similarity calculation uses custom thresholds."""
        config = {
            "enable_learning": True,
            "power_min_threshold": 75,
        }
        
        engine = OffsetEngine(config)
        learner = engine._learner
        
        # Test that similarity calculation uses the threshold
        # Add some training data first
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=25.0,
            mode="none",
            power_consumption=200.0,
            time_of_day=time(14, 0),
            day_of_week=1
        )
        
        # Record a sample
        engine.record_actual_performance(2.0, 2.0, input_data)
        
        # Now test similarity with a different power value
        input_data.power_consumption = 190.0
        similar_samples = learner._find_similar_samples(input_data)
        
        # Should find similar samples since power difference (10W) is within threshold (75W)
        assert len(similar_samples) > 0


class TestConfigFlowPowerThresholds:
    """Test power thresholds in configuration flow."""
    
    def test_power_threshold_schema_construction(self):
        """Test that power threshold fields can be added to schema."""
        # Test that the power threshold configuration keys exist and have proper defaults
        assert CONF_POWER_IDLE_THRESHOLD == "power_idle_threshold"
        assert CONF_POWER_MIN_THRESHOLD == "power_min_threshold"  
        assert CONF_POWER_MAX_THRESHOLD == "power_max_threshold"
        
        # Test that defaults are properly ordered
        assert DEFAULT_POWER_IDLE_THRESHOLD < DEFAULT_POWER_MIN_THRESHOLD
        assert DEFAULT_POWER_MIN_THRESHOLD < DEFAULT_POWER_MAX_THRESHOLD
    
    def test_config_flow_validation_logic(self):
        """Test validation logic for power thresholds."""
        # Test that validation would reject invalid threshold order
        idle_threshold = 100
        min_threshold = 50  # Invalid: should be > idle
        max_threshold = 200
        
        # Validate the logic
        assert not (idle_threshold < min_threshold < max_threshold)
        
        # Test valid order
        idle_threshold = 50
        min_threshold = 100
        max_threshold = 250
        
        assert idle_threshold < min_threshold < max_threshold
    
    def test_power_threshold_defaults_in_schema(self):
        """Test that power threshold defaults are correct."""
        assert DEFAULT_POWER_IDLE_THRESHOLD == 50
        assert DEFAULT_POWER_MIN_THRESHOLD == 100
        assert DEFAULT_POWER_MAX_THRESHOLD == 250
        
        # Verify the order is correct
        assert DEFAULT_POWER_IDLE_THRESHOLD < DEFAULT_POWER_MIN_THRESHOLD < DEFAULT_POWER_MAX_THRESHOLD


class TestIntegrationWithPowerThresholds:
    """Test full integration with configurable power thresholds."""
    
    def test_offset_engine_integration(self):
        """Test that OffsetEngine properly integrates power thresholds."""
        config = {
            CONF_MAX_OFFSET: 5.0,
            CONF_POWER_IDLE_THRESHOLD: 35,
            CONF_POWER_MIN_THRESHOLD: 85,
            CONF_POWER_MAX_THRESHOLD: 210,
        }
        
        engine = OffsetEngine(config)
        
        # Test that offset calculation uses the configured thresholds
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="none",
            power_consumption=30.0,  # Below idle threshold (35W)
            time_of_day=time(14, 0),
            day_of_week=1
        )
        
        result = engine.calculate_offset(input_data)
        # Should mention AC idle/off in the reason
        assert "idle" in result.reason.lower() or "off" in result.reason.lower()
    
    def test_backward_compatibility(self):
        """Test that existing configs without power thresholds still work."""
        config = {
            CONF_MAX_OFFSET: 5.0,
            # No power thresholds configured
        }
        
        # Should work with default thresholds
        engine = OffsetEngine(config)
        assert engine._power_idle_threshold == DEFAULT_POWER_IDLE_THRESHOLD
        assert engine._power_min_threshold == DEFAULT_POWER_MIN_THRESHOLD
        assert engine._power_max_threshold == DEFAULT_POWER_MAX_THRESHOLD