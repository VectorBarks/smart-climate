# ABOUTME: Test suite for ProbeResult v1.5.3 enhancements with outdoor_temp field
# ABOUTME: Validates backward compatibility and new outdoor temperature functionality

import pytest
from datetime import datetime, timezone
from dataclasses import fields, asdict
from typing import Optional

from custom_components.smart_climate.thermal_models import ProbeResult


def test_probe_result_accepts_outdoor_temp_parameter():
    """Test that ProbeResult accepts outdoor_temp parameter."""
    timestamp = datetime.now(timezone.utc)
    outdoor_temp = 25.5
    
    probe = ProbeResult(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False,
        timestamp=timestamp,
        outdoor_temp=outdoor_temp
    )
    
    assert probe.outdoor_temp == outdoor_temp
    assert probe.tau_value == 100.0
    assert probe.confidence == 0.8
    assert probe.duration == 1800
    assert probe.fit_quality == 0.9
    assert probe.aborted == False
    assert probe.timestamp == timestamp


def test_probe_result_outdoor_temp_defaults_to_none():
    """Test that outdoor_temp defaults to None for backward compatibility."""
    timestamp = datetime.now(timezone.utc)
    
    probe = ProbeResult(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False,
        timestamp=timestamp
    )
    
    assert probe.outdoor_temp is None
    assert probe.tau_value == 100.0
    assert probe.confidence == 0.8
    assert probe.duration == 1800
    assert probe.fit_quality == 0.9
    assert probe.aborted == False
    assert probe.timestamp == timestamp


def test_probe_result_remains_frozen():
    """Test that ProbeResult remains immutable (frozen)."""
    probe = ProbeResult(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False,
        outdoor_temp=25.5
    )
    
    # Verify the class is frozen
    assert ProbeResult.__dataclass_params__.frozen == True
    
    # Attempt to modify should raise FrozenInstanceError
    with pytest.raises(Exception):  # FrozenInstanceError
        probe.outdoor_temp = 30.0
    
    with pytest.raises(Exception):  # FrozenInstanceError
        probe.tau_value = 150.0


def test_probe_result_timestamp_auto_generates_utc():
    """Test that timestamp field auto-generates in UTC."""
    before_creation = datetime.now(timezone.utc)
    
    probe = ProbeResult(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False,
        outdoor_temp=25.5
    )
    
    after_creation = datetime.now(timezone.utc)
    
    # Timestamp should be between before and after
    assert before_creation <= probe.timestamp <= after_creation
    
    # Timestamp should be in UTC
    assert probe.timestamp.tzinfo == timezone.utc


def test_probe_result_all_fields_specified():
    """Test creating probe with all fields specified including outdoor_temp."""
    timestamp = datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    outdoor_temp = -5.2  # Test with negative temperature
    
    probe = ProbeResult(
        tau_value=75.5,
        confidence=0.95,
        duration=3600,
        fit_quality=0.85,
        aborted=True,
        timestamp=timestamp,
        outdoor_temp=outdoor_temp
    )
    
    assert probe.tau_value == 75.5
    assert probe.confidence == 0.95
    assert probe.duration == 3600
    assert probe.fit_quality == 0.85
    assert probe.aborted == True
    assert probe.timestamp == timestamp
    assert probe.outdoor_temp == outdoor_temp


def test_probe_result_minimal_fields_backward_compat():
    """Test creating probe with minimal fields for backward compatibility."""
    probe = ProbeResult(
        tau_value=90.0,
        confidence=0.7,
        duration=1200,
        fit_quality=0.8,
        aborted=False
    )
    
    # Required fields should be set
    assert probe.tau_value == 90.0
    assert probe.confidence == 0.7
    assert probe.duration == 1200
    assert probe.fit_quality == 0.8
    assert probe.aborted == False
    
    # Default fields should be set appropriately
    assert probe.outdoor_temp is None
    assert probe.timestamp.tzinfo == timezone.utc
    assert isinstance(probe.timestamp, datetime)


def test_probe_result_serialization_includes_outdoor_temp():
    """Test that serialization includes outdoor_temp when present."""
    timestamp = datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    outdoor_temp = 22.3
    
    probe = ProbeResult(
        tau_value=110.0,
        confidence=0.88,
        duration=2400,
        fit_quality=0.92,
        aborted=False,
        timestamp=timestamp,
        outdoor_temp=outdoor_temp
    )
    
    # Convert to dict (simulates serialization)
    probe_dict = asdict(probe)
    
    assert 'outdoor_temp' in probe_dict
    assert probe_dict['outdoor_temp'] == outdoor_temp
    assert probe_dict['tau_value'] == 110.0
    assert probe_dict['confidence'] == 0.88
    assert probe_dict['duration'] == 2400
    assert probe_dict['fit_quality'] == 0.92
    assert probe_dict['aborted'] == False
    assert probe_dict['timestamp'] == timestamp


def test_probe_result_serialization_handles_none_outdoor_temp():
    """Test that serialization includes outdoor_temp as None when not specified."""
    timestamp = datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    
    probe = ProbeResult(
        tau_value=110.0,
        confidence=0.88,
        duration=2400,
        fit_quality=0.92,
        aborted=False,
        timestamp=timestamp
    )
    
    # Convert to dict (simulates serialization)
    probe_dict = asdict(probe)
    
    assert 'outdoor_temp' in probe_dict
    assert probe_dict['outdoor_temp'] is None
    assert probe_dict['tau_value'] == 110.0
    assert probe_dict['confidence'] == 0.88
    assert probe_dict['duration'] == 2400
    assert probe_dict['fit_quality'] == 0.92
    assert probe_dict['aborted'] == False
    assert probe_dict['timestamp'] == timestamp


def test_probe_result_deserialization_handles_missing_outdoor_temp():
    """Test that deserialization handles missing outdoor_temp for legacy data."""
    # Simulate legacy probe data without outdoor_temp field
    legacy_data = {
        'tau_value': 95.0,
        'confidence': 0.82,
        'duration': 1500,
        'fit_quality': 0.87,
        'aborted': False,
        'timestamp': datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    }
    
    # Should be able to create ProbeResult from legacy data by using defaults
    probe = ProbeResult(
        tau_value=legacy_data['tau_value'],
        confidence=legacy_data['confidence'],
        duration=legacy_data['duration'],
        fit_quality=legacy_data['fit_quality'],
        aborted=legacy_data['aborted'],
        timestamp=legacy_data['timestamp']
        # outdoor_temp not specified - should default to None
    )
    
    assert probe.tau_value == 95.0
    assert probe.confidence == 0.82
    assert probe.duration == 1500
    assert probe.fit_quality == 0.87
    assert probe.aborted == False
    assert probe.timestamp == legacy_data['timestamp']
    assert probe.outdoor_temp is None


def test_probe_result_deserialization_with_outdoor_temp():
    """Test that deserialization works with outdoor_temp field present."""
    # Simulate new probe data with outdoor_temp field
    new_data = {
        'tau_value': 85.0,
        'confidence': 0.91,
        'duration': 1800,
        'fit_quality': 0.94,
        'aborted': False,
        'timestamp': datetime(2025, 8, 18, 12, 0, 0, tzinfo=timezone.utc),
        'outdoor_temp': 18.7
    }
    
    probe = ProbeResult(
        tau_value=new_data['tau_value'],
        confidence=new_data['confidence'],
        duration=new_data['duration'],
        fit_quality=new_data['fit_quality'],
        aborted=new_data['aborted'],
        timestamp=new_data['timestamp'],
        outdoor_temp=new_data['outdoor_temp']
    )
    
    assert probe.tau_value == 85.0
    assert probe.confidence == 0.91
    assert probe.duration == 1800
    assert probe.fit_quality == 0.94
    assert probe.aborted == False
    assert probe.timestamp == new_data['timestamp']
    assert probe.outdoor_temp == 18.7


def test_probe_result_outdoor_temp_field_type():
    """Test that outdoor_temp field has correct type annotation."""
    # Check that outdoor_temp field exists and has correct type
    probe_fields = {field.name: field for field in fields(ProbeResult)}
    
    assert 'outdoor_temp' in probe_fields
    outdoor_temp_field = probe_fields['outdoor_temp']
    
    # Check type annotation is Optional[float]
    assert outdoor_temp_field.type == Optional[float]
    
    # Check default value is None
    assert outdoor_temp_field.default is None


def test_probe_result_field_ordering_maintains_compatibility():
    """Test that field ordering maintains compatibility with existing code."""
    # Get all field names in order
    field_names = [field.name for field in fields(ProbeResult)]
    
    # Original fields should come first in the same order
    expected_original_fields = [
        'tau_value',
        'confidence', 
        'duration',
        'fit_quality',
        'aborted',
        'timestamp'
    ]
    
    # Check that original fields are in the correct order
    for i, expected_field in enumerate(expected_original_fields):
        assert field_names[i] == expected_field, (
            f"Field order changed: expected {expected_field} at position {i}, "
            f"got {field_names[i]}"
        )
    
    # outdoor_temp should be the last field
    assert field_names[-1] == 'outdoor_temp'
    assert len(field_names) == 7  # 6 original + 1 new field