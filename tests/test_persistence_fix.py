"""Test persistence fix for learning data."""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile
from datetime import datetime

from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.data_store import SmartClimateDataStore


@pytest.mark.asyncio
async def test_persistence_round_trip():
    """Test that learning data survives save and load cycle."""
    
    # Create temporary directory for test data
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir) / "smart_climate"
        data_dir.mkdir()
        
        # Create mock hass with config path
        mock_hass = Mock()
        mock_hass.async_add_executor_job = AsyncMock(side_effect=lambda f, *args: f(*args))
        mock_hass.config.config_dir = str(tmpdir)  # Set config_dir to temp directory
        mock_hass.config.path = Mock(return_value=str(data_dir))
        
        # Create data store
        entity_id = "climate.test"
        data_store = SmartClimateDataStore(mock_hass, entity_id)
        
        # Create offset engine with learning enabled
        config = {
            "enable_learning": True,
            "max_offset": 5.0
        }
        engine = OffsetEngine(config)
        engine.set_data_store(data_store)
        
        # Create some test learning data
        test_learner_data = {
            "version": "1.2",
            "time_patterns": {12: 0.02, 13: -0.195},
            "time_pattern_counts": {12: 1, 13: 1},
            "temp_correlation_data": [
                {"outdoor_temp": 26.17, "offset": 0.02},
                {"outdoor_temp": 27.22, "offset": -0.195}
            ],
            "power_state_patterns": {
                "cooling": {"avg_offset": 0.02, "count": 1},
                "idle": {"avg_offset": -0.195, "count": 1}
            },
            "enhanced_samples": [
                {
                    "predicted": 0.02,
                    "actual": 0.02,
                    "ac_temp": 25.0,
                    "room_temp": 24.98,
                    "outdoor_temp": 26.17,
                    "mode": "none",
                    "power": 378.0,
                    "hysteresis_state": "idle_stable_zone",
                    "indoor_humidity": 45.37,
                    "outdoor_humidity": 46.35,
                    "timestamp": "2025-08-29T12:34:08.166288"
                },
                {
                    "predicted": -0.195,
                    "actual": -0.195,
                    "ac_temp": 25.0,
                    "room_temp": 25.195,
                    "outdoor_temp": 27.22,
                    "mode": "none",
                    "power": 16.0,
                    "hysteresis_state": "idle_above_start_threshold",
                    "indoor_humidity": 45.92,
                    "outdoor_humidity": 44.52,
                    "timestamp": "2025-08-29T13:05:37.522530"
                }
            ],
            "sample_count": 2
        }
        
        # Mock the learner to return test data
        if not engine._learner:
            from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner
            engine._learner = LightweightOffsetLearner()
        
        engine._learner.serialize_for_persistence = Mock(return_value=test_learner_data)
        
        # Save the data
        await engine.async_save_learning_data()
        
        # Verify file was created
        save_file = data_dir / f"smart_climate_{entity_id.replace('.', '_')}.json"
        assert save_file.exists(), "Save file should exist"
        
        # Load the raw file to check structure
        with save_file.open() as f:
            raw_data = json.load(f)
        
        print("Raw saved data structure:")
        print(json.dumps(raw_data, indent=2))
        
        # Verify outer structure from data_store
        assert raw_data["version"] == "1.0", "Outer version should be 1.0 from data_store"
        assert raw_data["entity_id"] == entity_id
        assert "learning_data" in raw_data
        
        # Verify inner structure from offset_engine
        inner_data = raw_data["learning_data"]
        assert inner_data["version"] == "2.1", "Inner version should be 2.1 from offset_engine"
        assert "learning_data" in inner_data
        assert "learner_data" in inner_data["learning_data"]
        
        # Create a new engine to test loading
        engine2 = OffsetEngine(config)
        engine2.set_data_store(data_store)
        
        # Mock the learner restore
        if not engine2._learner:
            from custom_components.smart_climate.lightweight_learner import LightweightOffsetLearner
            engine2._learner = LightweightOffsetLearner()
        
        engine2._learner.restore_from_persistence = Mock(return_value=True)
        
        # Load the data
        success = await engine2.async_load_learning_data()
        
        assert success, "Load should succeed"
        
        # Verify restore was called with the correct data
        engine2._learner.restore_from_persistence.assert_called_once()
        restored_data = engine2._learner.restore_from_persistence.call_args[0][0]
        
        # Verify the restored data matches what we saved
        assert restored_data == test_learner_data, "Restored data should match saved data"
        
        print("\n✅ Persistence round trip successful!")
        print(f"Saved 2 samples, restored 2 samples")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_persistence_round_trip())