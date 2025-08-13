"""Integration tests for humidity data flow through the system."""

import pytest
from datetime import time
from unittest.mock import Mock

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.models import OffsetInput
from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner


class TestHumidityIntegration:
    """Test humidity data integration across the system."""

    def test_offset_engine_humidity_data_flow(self):
        """Test that humidity data flows from OffsetInput through OffsetEngine to LightweightLearner."""
        # Create OffsetEngine configuration with learning enabled
        config = {
            "ml_enabled": True,
            "enable_learning": True
        }
        
        # Create OffsetEngine with learning enabled
        engine = OffsetEngine(config)
        
        # Verify the learner was created
        assert engine._learner is not None
        assert isinstance(engine._learner, LightweightOffsetLearner)
        
        # Create input data with humidity
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode='cool',
            power_consumption=250.0,
            time_of_day=time(14, 0),
            day_of_week=1,
            indoor_humidity=45.0,
            outdoor_humidity=65.0
        )
        
        # Test that offset calculation works with humidity data
        result = engine.calculate_offset(input_data)
        
        # Verify result structure
        assert hasattr(result, 'offset')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'clamped')
        
        # Record actual performance to test learning
        engine.record_actual_performance(
            predicted_offset=result.offset,
            actual_offset=1.2,  # Different from predicted to test learning
            input_data=input_data
        )
        
        # Verify humidity data was stored in the learner
        learner_samples = engine._learner._enhanced_samples
        assert len(learner_samples) == 1
        
        sample = learner_samples[0]
        assert sample["indoor_humidity"] == 45.0
        assert sample["outdoor_humidity"] == 65.0
        
        # Verify all other data was also stored correctly
        assert sample["ac_temp"] == 22.0
        assert sample["room_temp"] == 24.0
        assert sample["outdoor_temp"] == 30.0
        assert sample["mode"] == "cool"
        assert sample["power"] == 250.0

    def test_offset_engine_humidity_prediction_with_data(self):
        """Test that OffsetEngine can make predictions using humidity data."""
        # Create OffsetEngine configuration with learning enabled
        config = {
            "ml_enabled": True,
            "enable_learning": True
        }
        
        # Create OffsetEngine with learning enabled
        engine = OffsetEngine(config)
        
        # Add some training data with humidity
        training_data = [
            (22.0, 24.0, 30.0, 45.0, 65.0, 1.2),  # ac_temp, room_temp, outdoor_temp, indoor_hum, outdoor_hum, offset
            (22.5, 24.5, 31.0, 46.0, 66.0, 1.3),
            (23.0, 25.0, 32.0, 47.0, 67.0, 1.4),
        ]
        
        for ac_temp, room_temp, outdoor_temp, indoor_hum, outdoor_hum, offset in training_data:
            input_data = OffsetInput(
                ac_internal_temp=ac_temp,
                room_temp=room_temp,
                outdoor_temp=outdoor_temp,
                mode='cool',
                power_consumption=250.0,
                time_of_day=time(14, 0),
                day_of_week=1,
                indoor_humidity=indoor_hum,
                outdoor_humidity=outdoor_hum
            )
            
            # Record the actual performance for training
            engine.record_actual_performance(
                predicted_offset=0.0,  # Assume no initial prediction
                actual_offset=offset,
                input_data=input_data
            )
        
        # Now test prediction with similar conditions
        prediction_input = OffsetInput(
            ac_internal_temp=22.1,
            room_temp=24.1,
            outdoor_temp=30.1,
            mode='cool',
            power_consumption=250.0,
            time_of_day=time(14, 0),
            day_of_week=1,
            indoor_humidity=45.1,  # Similar humidity
            outdoor_humidity=65.1
        )
        
        # Calculate offset - should use learned patterns including humidity
        result = engine.calculate_offset(prediction_input)
        
        # The prediction should be influenced by the training data
        # With similar conditions, it should predict something close to the training offsets
        assert result.offset != 0.0  # Should have learned something
        
        # Verify confidence is reasonable
        assert 0.0 <= result.confidence <= 1.0

    def test_offset_engine_humidity_persistence(self):
        """Test that humidity data persists through learner serialization."""
        # Create OffsetEngine configuration with learning enabled
        config = {
            "ml_enabled": True,
            "enable_learning": True
        }
        
        # Create first OffsetEngine instance
        engine1 = OffsetEngine(config)
        
        # Add sample with humidity data
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode='cool',
            power_consumption=250.0,
            time_of_day=time(14, 0),
            day_of_week=1,
            indoor_humidity=45.0,
            outdoor_humidity=65.0
        )
        
        engine1.record_actual_performance(
            predicted_offset=1.0,
            actual_offset=1.2,
            input_data=input_data
        )
        
        # Get serialized data from the learner directly
        serialized_data = engine1._learner.serialize_for_persistence()
        
        # Verify humidity data is in serialized format
        assert "enhanced_samples" in serialized_data
        assert len(serialized_data["enhanced_samples"]) == 1
        
        sample = serialized_data["enhanced_samples"][0]
        assert sample["indoor_humidity"] == 45.0
        assert sample["outdoor_humidity"] == 65.0
        
        # Create second OffsetEngine instance and restore data
        engine2 = OffsetEngine(config)
        
        # Restore the data to the learner
        restore_success = engine2._learner.restore_from_persistence(serialized_data)
        assert restore_success is True
        
        # Verify humidity data was restored
        restored_samples = engine2._learner._enhanced_samples
        assert len(restored_samples) == 1
        
        restored_sample = restored_samples[0]
        assert restored_sample["indoor_humidity"] == 45.0
        assert restored_sample["outdoor_humidity"] == 65.0

    def test_offset_engine_with_none_humidity_values(self):
        """Test that OffsetEngine handles None humidity values gracefully."""
        # Create OffsetEngine configuration with learning enabled
        config = {
            "ml_enabled": True,
            "enable_learning": True
        }
        
        # Create OffsetEngine with learning enabled
        engine = OffsetEngine(config)
        
        # Create input data without humidity (None values)
        input_data = OffsetInput(
            ac_internal_temp=22.0,
            room_temp=24.0,
            outdoor_temp=30.0,
            mode='cool',
            power_consumption=250.0,
            time_of_day=time(14, 0),
            day_of_week=1,
            indoor_humidity=None,
            outdoor_humidity=None
        )
        
        # Should work without errors
        result = engine.calculate_offset(input_data)
        assert result.offset is not None
        
        # Record actual performance
        engine.record_actual_performance(
            predicted_offset=result.offset,
            actual_offset=1.2,
            input_data=input_data
        )
        
        # Verify None humidity values were stored
        learner_samples = engine._learner._enhanced_samples
        assert len(learner_samples) == 1
        
        sample = learner_samples[0]
        assert sample["indoor_humidity"] is None
        assert sample["outdoor_humidity"] is None



    def test_coordinator_humidity_update_integration_in_models(self):
        """Test that SmartClimateData model includes humidity_data field."""
        from custom_components.smart_climate.models import SmartClimateData
        import inspect
        
        # Get dataclass fields
        sig = inspect.signature(SmartClimateData.__init__)
        
        # Verify humidity_data parameter exists
        assert 'humidity_data' in sig.parameters
        
        # Verify it's optional with None default
        humidity_data_param = sig.parameters['humidity_data']
        assert humidity_data_param.default is None
        
        # Test creating SmartClimateData with humidity_data
        data = SmartClimateData(
            room_temp=22.0,
            outdoor_temp=30.0,
            power=250.0,
            calculated_offset=1.5,
            mode_adjustments=None,
            humidity_data={"indoor_humidity": 45.0, "triggers": ["humidity_change"]}
        )
        
        assert data.humidity_data is not None
        assert data.humidity_data["indoor_humidity"] == 45.0
        assert data.humidity_data["triggers"] == ["humidity_change"]

