"""Integration tests for confidence value display in Smart Climate Control.

ABOUTME: Tests end-to-end confidence flow from LightweightLearner through dashboard sensors.
Verifies confidence calculation, updates, persistence, and UI display.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.const import Platform

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.models import OffsetInput, OffsetResult
from custom_components.smart_climate.lightweight_learner import (
    LightweightOffsetLearner,
    OffsetPrediction,
)
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.sensor import AccuracyCurrentSensor
from custom_components.smart_climate.switch import LearningSwitch
from custom_components.smart_climate.data_store import SmartClimateDataStore


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.states = Mock()
    hass.services = Mock()
    return hass


@pytest.fixture
def mock_coordinator(mock_hass):
    """Create a mock DataUpdateCoordinator with dashboard data."""
    coordinator = MagicMock(spec=DataUpdateCoordinator)
    coordinator.hass = mock_hass
    coordinator.last_update_success = True
    coordinator.data = {
        "calculated_offset": 1.5,
        "learning_info": {
            "enabled": True,
            "samples": 50,
            "accuracy": 0.75,  # This is the confidence value
            "confidence": 0.75,
            "has_sufficient_data": True,
            "last_sample_time": "2025-07-10T12:00:00",
        },
        "save_diagnostics": {
            "save_count": 5,
            "failed_save_count": 0,
            "last_save_time": "2025-07-10T11:30:00",
        },
        "calibration_info": {
            "in_calibration": False,
            "cached_offset": None,
        },
    }
    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock()
    entry.entry_id = "test_entry"
    entry.unique_id = "test_unique"
    entry.title = "Test Climate"
    entry.data = {
        "climate_entity": "climate.test_ac",
        "room_sensor": "sensor.room_temp",
        "enable_learning": True,
    }
    return entry


class TestConfidenceFlowIntegration:
    """Test confidence value flow from learning engine to UI."""

    def test_lightweight_learner_confidence_calculation(self):
        """Test that LightweightLearner calculates confidence correctly."""
        learner = LightweightOffsetLearner()
        
        # Add some samples to build confidence
        for i in range(10):
            learner.add_sample(
                predicted=1.0,
                actual=1.2,
                ac_temp=22.0,
                room_temp=23.0,
                outdoor_temp=30.0,
                mode="cool",
                power=1500.0,
            )
        
        # Test prediction with confidence
        prediction = learner.predict_offset(
            outdoor_temp=30.0,
            hour=12,
            power_state="high"
        )
        
        assert isinstance(prediction, OffsetPrediction)
        assert 0.0 <= prediction.confidence <= 1.0
        assert prediction.confidence > 0.1  # Should have some confidence with samples
        assert prediction.reason != "no patterns available"

    def test_offset_engine_passes_confidence(self):
        """Test that OffsetEngine correctly passes confidence from learner."""
        # Create OffsetEngine with learning enabled
        config = {
            "enable_learning": True,
            "max_offset": 5.0,
        }
        engine = OffsetEngine(config)
        
        # Mock the learner to return a specific confidence
        mock_learner = Mock(spec=LightweightOffsetLearner)
        mock_learner.predict_offset.return_value = OffsetPrediction(
            predicted_offset=1.5,
            confidence=0.85,
            reason="time-based pattern"
        )
        mock_learner.get_stats.return_value = {
            "samples": 100,
            "accuracy": 0.9,
            "has_sufficient_data": True,
            "last_sample_time": "2025-07-10T12:00:00",
        }
        engine._learner = mock_learner
        
        # Calculate offset
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=1500.0,
            time_of_day=datetime.now().time(),
            day_of_week=1,
        )
        
        result = engine.calculate_offset(input_data)
        
        # Verify confidence is included in result
        assert isinstance(result, OffsetResult)
        assert 0.0 <= result.confidence <= 1.0
        # Confidence should be influenced by learner's confidence
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_dashboard_data_includes_confidence(self):
        """Test that async_get_dashboard_data includes confidence/accuracy."""
        config = {
            "enable_learning": True,
            "max_offset": 5.0,
        }
        engine = OffsetEngine(config)
        
        # Add some learning samples
        engine._sample_count = 50
        if engine._learner:
            # Mock learner stats
            engine._learner.get_stats = Mock(return_value={
                "samples": 50,
                "accuracy": 0.75,
                "has_sufficient_data": True,
                "last_sample_time": "2025-07-10T12:00:00",
            })
        
        # Get dashboard data
        dashboard_data = await engine.async_get_dashboard_data()
        
        # Verify confidence is included
        assert "learning_info" in dashboard_data
        assert "accuracy" in dashboard_data["learning_info"]
        assert "confidence" in dashboard_data["learning_info"]
        
        # Both should have the same value
        accuracy = dashboard_data["learning_info"]["accuracy"]
        confidence = dashboard_data["learning_info"]["confidence"]
        assert accuracy == confidence
        assert 0.0 <= accuracy <= 1.0

    def test_accuracy_sensor_displays_confidence(self, mock_coordinator, mock_config_entry):
        """Test that AccuracyCurrentSensor correctly displays confidence as percentage."""
        sensor = AccuracyCurrentSensor(
            mock_coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Check sensor value (should be confidence as percentage)
        value = sensor.native_value
        assert value == 75  # 0.75 * 100
        
        # Check attributes
        attrs = sensor.extra_state_attributes
        assert attrs["confidence_factor"] == 0.75
        assert attrs["learning_enabled"] is True
        assert attrs["samples_collected"] == 50

    def test_switch_entity_shows_confidence(self, mock_hass, mock_config_entry):
        """Test that learning switch entity shows confidence in attributes."""
        # Create mock offset engine
        mock_engine = Mock(spec=OffsetEngine)
        mock_engine._enable_learning = True
        mock_engine._sample_count = 50
        mock_engine.get_learning_stats.return_value = {
            "samples_collected": 50,
            "patterns_learned": 5,
            "avg_accuracy": 0.82,
            "confidence": 0.82,
            "last_sample_time": "2025-07-10T12:00:00",
        }
        
        # Create switch
        switch = LearningSwitch(
            mock_config_entry,
            mock_engine,
            "Test Climate",
            "climate.test_ac"
        )
        
        # Check state
        assert switch.is_on is True
        
        # Check attributes include confidence
        attrs = switch.extra_state_attributes
        assert "confidence" in attrs
        assert attrs["confidence"] == "82%"
        assert attrs["samples_collected"] == 50
        assert attrs["avg_accuracy"] == "82%"

    @pytest.mark.asyncio
    async def test_confidence_updates_with_new_samples(self):
        """Test that confidence updates when new samples are added."""
        config = {
            "enable_learning": True,
            "max_offset": 5.0,
        }
        engine = OffsetEngine(config)
        
        # Initial dashboard data
        initial_data = await engine.async_get_dashboard_data()
        initial_confidence = initial_data["learning_info"]["confidence"]
        
        # Add feedback samples
        for i in range(20):
            engine.add_feedback(
                predicted_offset=1.0,
                actual_offset=1.1,
                ac_temp=22.0,
                room_temp=23.0,
                outdoor_temp=30.0,
                mode="cool",
                power=1500.0,
            )
        
        # Get updated dashboard data
        updated_data = await engine.async_get_dashboard_data()
        updated_confidence = updated_data["learning_info"]["confidence"]
        
        # Confidence should have changed (likely increased)
        assert updated_confidence != initial_confidence
        assert updated_confidence > 0  # Should have some confidence with samples

    @pytest.mark.asyncio
    async def test_confidence_persists_across_save_load(self, tmp_path):
        """Test that confidence calculation is consistent after save/load."""
        # Create data store
        store_path = tmp_path / "test_data.json"
        data_store = SmartClimateDataStore(str(store_path))
        
        # Create engine with learning
        config = {
            "enable_learning": True,
            "max_offset": 5.0,
        }
        engine1 = OffsetEngine(config)
        engine1.set_data_store(data_store)
        
        # Add samples to build confidence
        for i in range(30):
            engine1.add_feedback(
                predicted_offset=1.5,
                actual_offset=1.6,
                ac_temp=22.0,
                room_temp=23.5,
                outdoor_temp=30.0,
                mode="cool",
                power=1500.0,
            )
        
        # Get confidence before save
        data_before = await engine1.async_get_dashboard_data()
        confidence_before = data_before["learning_info"]["confidence"]
        samples_before = data_before["learning_info"]["samples"]
        
        # Save data
        await engine1.async_save_learning_data()
        
        # Create new engine and load data
        engine2 = OffsetEngine(config)
        engine2.set_data_store(data_store)
        await engine2.async_load_learning_data()
        
        # Get confidence after load
        data_after = await engine2.async_get_dashboard_data()
        confidence_after = data_after["learning_info"]["confidence"]
        samples_after = data_after["learning_info"]["samples"]
        
        # Verify persistence
        assert samples_after == samples_before
        assert confidence_after == pytest.approx(confidence_before, rel=0.1)
        assert confidence_after > 0  # Should maintain confidence

    @pytest.mark.asyncio
    async def test_coordinator_updates_propagate_confidence(self, mock_hass):
        """Test that coordinator updates propagate confidence to sensors."""
        # Set up entry data
        mock_hass.data[DOMAIN] = {
            "test_entry": {
                "coordinators": {},
            }
        }
        
        # Create a real coordinator with mock offset engine
        mock_engine = Mock(spec=OffsetEngine)
        initial_confidence = 0.5
        mock_engine.async_get_dashboard_data = Mock(return_value={
            "calculated_offset": 1.0,
            "learning_info": {
                "enabled": True,
                "samples": 10,
                "accuracy": initial_confidence,
                "confidence": initial_confidence,
                "has_sufficient_data": True,
            },
            "save_diagnostics": {},
            "calibration_info": {},
        })
        
        # Create coordinator
        from custom_components.smart_climate.coordinator import SmartClimateCoordinator
        coordinator = SmartClimateCoordinator(
            mock_hass,
            mock_engine,
            "climate.test_ac",
            30  # update interval
        )
        
        # Initial update
        await coordinator.async_config_entry_first_refresh()
        
        # Create sensor
        sensor = AccuracyCurrentSensor(
            coordinator,
            "climate.test_ac",
            Mock(unique_id="test", title="Test")
        )
        
        # Check initial value
        assert sensor.native_value == 50  # 0.5 * 100
        
        # Update confidence in engine
        updated_confidence = 0.85
        mock_engine.async_get_dashboard_data.return_value["learning_info"]["accuracy"] = updated_confidence
        mock_engine.async_get_dashboard_data.return_value["learning_info"]["confidence"] = updated_confidence
        
        # Force coordinator update
        await coordinator.async_refresh()
        
        # Check sensor updated
        assert sensor.native_value == 85  # 0.85 * 100

    def test_confidence_calculation_with_limited_data(self):
        """Test confidence calculation with limited training data."""
        learner = LightweightOffsetLearner()
        
        # Test with no data
        prediction_no_data = learner.predict_offset(
            outdoor_temp=25.0,
            hour=12,
            power_state="idle"
        )
        assert prediction_no_data.confidence == 0.1  # Minimum confidence
        assert "no training data" in prediction_no_data.reason
        
        # Add just one sample
        learner.add_sample(
            predicted=1.0,
            actual=1.0,
            ac_temp=22.0,
            room_temp=23.0,
            outdoor_temp=25.0,
            mode="cool",
            power=100.0,
        )
        
        # Test with minimal data
        prediction_minimal = learner.predict_offset(
            outdoor_temp=25.0,
            hour=12,
            power_state="idle"
        )
        assert 0.1 < prediction_minimal.confidence < 0.5  # Low but not minimum
        assert "limited data" in prediction_minimal.reason or "time-based pattern" in prediction_minimal.reason

    def test_confidence_factors_combination(self):
        """Test how different factors contribute to confidence calculation."""
        learner = LightweightOffsetLearner()
        
        # Add diverse samples to build different pattern types
        # Time patterns
        for hour in range(24):
            learner.add_sample(
                predicted=1.0 + hour * 0.1,
                actual=1.0 + hour * 0.1,
                ac_temp=22.0,
                room_temp=23.0 + hour * 0.1,
                outdoor_temp=None,  # No outdoor temp
                mode="cool",
                power=None,  # No power
            )
        
        # Temperature correlation patterns
        for temp in range(20, 35):
            learner.add_sample(
                predicted=2.0,
                actual=2.0,
                ac_temp=22.0,
                room_temp=23.0,
                outdoor_temp=float(temp),
                mode="cool",
                power=None,
            )
        
        # Power state patterns
        for power in [100, 500, 1000, 1500]:
            learner.add_sample(
                predicted=1.5,
                actual=1.5,
                ac_temp=22.0,
                room_temp=23.0,
                outdoor_temp=None,
                mode="cool",
                power=float(power),
            )
        
        # Test prediction with all factors available
        prediction_all = learner.predict_offset(
            outdoor_temp=28.0,
            hour=14,
            power_state="high"
        )
        
        # Should have high confidence with multiple pattern types
        assert prediction_all.confidence > 0.7
        assert "time-based pattern" in prediction_all.reason
        assert "temperature correlation" in prediction_all.reason
        assert "power state pattern" in prediction_all.reason
        
        # Test with only time pattern
        prediction_time_only = learner.predict_offset(
            outdoor_temp=None,
            hour=14,
            power_state=None
        )
        
        # Should have lower confidence with single factor
        assert prediction_time_only.confidence < prediction_all.confidence
        assert "time-based pattern" in prediction_time_only.reason


class TestConfidenceEdgeCases:
    """Test edge cases in confidence calculation and display."""

    def test_confidence_with_contradictory_patterns(self):
        """Test confidence when patterns contradict each other."""
        learner = LightweightOffsetLearner()
        
        # Add contradictory samples for the same hour
        for i in range(10):
            # Half say offset should be positive
            learner.add_sample(
                predicted=2.0,
                actual=2.0 if i % 2 == 0 else -2.0,
                ac_temp=22.0,
                room_temp=23.0,
                outdoor_temp=30.0,
                mode="cool",
                power=1500.0,
            )
        
        prediction = learner.predict_offset(
            outdoor_temp=30.0,
            hour=datetime.now().hour,
            power_state="high"
        )
        
        # Confidence should be lower due to inconsistency
        assert prediction.confidence < 0.7

    @pytest.mark.asyncio
    async def test_confidence_display_with_learning_disabled(self, mock_hass, mock_config_entry):
        """Test confidence display when learning is disabled."""
        # Create engine with learning disabled
        config = {
            "enable_learning": False,
            "max_offset": 5.0,
        }
        engine = OffsetEngine(config)
        
        # Get dashboard data
        data = await engine.async_get_dashboard_data()
        
        # Should show zero confidence when learning disabled
        assert data["learning_info"]["enabled"] is False
        assert data["learning_info"]["confidence"] == 0.0
        assert data["learning_info"]["accuracy"] == 0.0

    def test_sensor_handles_missing_confidence_data(self, mock_config_entry):
        """Test sensor gracefully handles missing confidence data."""
        # Create coordinator with incomplete data
        coordinator = MagicMock()
        coordinator.last_update_success = True
        coordinator.data = {
            "learning_info": {}  # Missing accuracy/confidence
        }
        
        sensor = AccuracyCurrentSensor(
            coordinator,
            "climate.test_ac",
            mock_config_entry
        )
        
        # Should return 0 when data missing
        assert sensor.native_value == 0
        
        # Test with no learning_info at all
        coordinator.data = {}
        assert sensor.native_value == 0
        
        # Test with coordinator.data = None
        coordinator.data = None
        assert sensor.native_value == 0

    @pytest.mark.asyncio
    async def test_confidence_calculation_after_error_recovery(self):
        """Test confidence calculation recovers after errors."""
        config = {
            "enable_learning": True,
            "max_offset": 5.0,
        }
        engine = OffsetEngine(config)
        
        # Force an error in the learner
        if engine._learner:
            engine._learner.predict_offset = Mock(side_effect=ValueError("Test error"))
        
        # Calculate offset should handle error
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode="cool",
            power_consumption=1500.0,
            time_of_day=datetime.now().time(),
            day_of_week=1,
        )
        
        result = engine.calculate_offset(input_data)
        assert result.confidence < 1.0  # Should have reduced confidence after error
        
        # Fix the learner
        if engine._learner:
            engine._learner.predict_offset = Mock(return_value=OffsetPrediction(
                predicted_offset=1.5,
                confidence=0.8,
                reason="recovered"
            ))
        
        # Should recover
        result2 = engine.calculate_offset(input_data)
        assert result2.confidence > result.confidence

    def test_confidence_percentage_rounding(self, mock_coordinator, mock_config_entry):
        """Test that confidence percentage is properly rounded for display."""
        # Test various confidence values
        test_cases = [
            (0.754, 75),   # Round down
            (0.755, 76),   # Round up  
            (0.999, 100),  # Near maximum
            (0.001, 0),    # Near minimum
            (0.505, 51),   # Exact middle
        ]
        
        for confidence, expected_percentage in test_cases:
            mock_coordinator.data["learning_info"]["accuracy"] = confidence
            mock_coordinator.data["learning_info"]["confidence"] = confidence
            
            sensor = AccuracyCurrentSensor(
                mock_coordinator,
                "climate.test_ac",
                mock_config_entry
            )
            
            assert sensor.native_value == expected_percentage
