# ABOUTME: Test suite for ProbeResult consistency across thermal_model.py and thermal_models.py
# ABOUTME: Ensures both modules have identical ProbeResult definitions per architecture §19.2

import pytest
from datetime import datetime, timezone
from dataclasses import fields


def test_probe_result_consistency_across_modules():
    """Test that ProbeResult definitions are identical in both thermal modules.
    
    This test ensures that thermal_model.py and thermal_models.py have identical
    ProbeResult class definitions as required by architecture §19.2.
    """
    # Import ProbeResult from both modules
    from custom_components.smart_climate.thermal_model import ProbeResult as ProbeResultModel
    from custom_components.smart_climate.thermal_models import ProbeResult as ProbeResultModels
    
    # Check that both classes have identical field names
    model_fields = {field.name for field in fields(ProbeResultModel)}
    models_fields = {field.name for field in fields(ProbeResultModels)}
    
    assert model_fields == models_fields, (
        f"ProbeResult field names differ: "
        f"thermal_model.py={model_fields}, thermal_models.py={models_fields}"
    )
    
    # Check that both classes have identical field types
    for field in fields(ProbeResultModel):
        model_field = field
        models_field = next(f for f in fields(ProbeResultModels) if f.name == field.name)
        
        assert model_field.type == models_field.type, (
            f"Field '{field.name}' has different types: "
            f"thermal_model.py={model_field.type}, thermal_models.py={models_field.type}"
        )
        
        # Check default values/factories match
        assert model_field.default == models_field.default, (
            f"Field '{field.name}' has different defaults: "
            f"thermal_model.py={model_field.default}, thermal_models.py={models_field.default}"
        )
        
        assert model_field.default_factory == models_field.default_factory, (
            f"Field '{field.name}' has different default_factory: "
            f"thermal_model.py={model_field.default_factory}, thermal_models.py={models_field.default_factory}"
        )
    
    # Check that both classes are frozen (immutable)
    assert ProbeResultModel.__dataclass_params__.frozen == True, (
        "thermal_model.ProbeResult should be frozen=True"
    )
    assert ProbeResultModels.__dataclass_params__.frozen == True, (
        "thermal_models.ProbeResult should be frozen=True"
    )
    
    # Test creating instances with timestamp field works identically
    timestamp = datetime.now(timezone.utc)
    
    probe_model = ProbeResultModel(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False,
        timestamp=timestamp
    )
    
    probe_models = ProbeResultModels(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False,
        timestamp=timestamp
    )
    
    # Both instances should have identical field values
    assert probe_model.tau_value == probe_models.tau_value
    assert probe_model.confidence == probe_models.confidence
    assert probe_model.duration == probe_models.duration
    assert probe_model.fit_quality == probe_models.fit_quality
    assert probe_model.aborted == probe_models.aborted
    assert probe_model.timestamp == probe_models.timestamp
    
    # Test automatic timestamp generation works identically
    probe_model_auto = ProbeResultModel(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False
    )
    
    probe_models_auto = ProbeResultModels(
        tau_value=100.0,
        confidence=0.8,
        duration=1800,
        fit_quality=0.9,
        aborted=False
    )
    
    # Both should have timestamp fields with timezone info
    assert probe_model_auto.timestamp.tzinfo is not None
    assert probe_models_auto.timestamp.tzinfo is not None
    assert probe_model_auto.timestamp.tzinfo == timezone.utc
    assert probe_models_auto.timestamp.tzinfo == timezone.utc


def test_probe_result_timestamp_field_exists():
    """Test that both ProbeResult classes have timestamp field.
    
    This test ensures the timestamp field enhancement has been applied
    to both thermal modules.
    """
    from custom_components.smart_climate.thermal_model import ProbeResult as ProbeResultModel
    from custom_components.smart_climate.thermal_models import ProbeResult as ProbeResultModels
    
    # Check timestamp field exists in both classes
    model_field_names = {field.name for field in fields(ProbeResultModel)}
    models_field_names = {field.name for field in fields(ProbeResultModels)}
    
    assert 'timestamp' in model_field_names, "thermal_model.ProbeResult missing timestamp field"
    assert 'timestamp' in models_field_names, "thermal_models.ProbeResult missing timestamp field"
    
    # Check timestamp field has correct type
    model_timestamp_field = next(f for f in fields(ProbeResultModel) if f.name == 'timestamp')
    models_timestamp_field = next(f for f in fields(ProbeResultModels) if f.name == 'timestamp')
    
    assert model_timestamp_field.type == datetime
    assert models_timestamp_field.type == datetime