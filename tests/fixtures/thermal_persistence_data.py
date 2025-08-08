"""ABOUTME: Test data generators for thermal persistence testing.
ABOUTME: Provides v1.0/v2.1 data formats, corruption scenarios, and migration test cases."""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock


# V1.0 format test data (legacy learning data only)
@pytest.fixture
def v1_persistence_data():
    """Valid v1.0 persistence data (old format without thermal_data section)."""
    return {
        "version": "1.0",
        "entity_id": "climate.living_room",
        "last_updated": "2025-08-08T16:00:00Z",
        "learning_data": {
            "samples": 45,
            "accuracy": 0.85,
            "last_sample_time": "2025-08-08T15:45:00Z",
            "model_weights": [0.2, 0.3, 0.1, 0.4],
            "hysteresis_data": {
                "learned_start_threshold": 24.5,
                "learned_stop_threshold": 23.5,
                "samples_collected": 20
            }
        }
    }


# V2.1 format test data (with thermal_data section)
@pytest.fixture
def v2_persistence_data():
    """Valid v2.1 persistence data (new format with thermal_data section)."""
    return {
        "version": "2.1",
        "entity_id": "climate.living_room", 
        "last_updated": "2025-08-08T16:00:00Z",
        "learning_data": {
            "samples": 45,
            "accuracy": 0.85,
            "last_sample_time": "2025-08-08T15:45:00Z",
            "model_weights": [0.2, 0.3, 0.1, 0.4],
            "hysteresis_data": {
                "learned_start_threshold": 24.5,
                "learned_stop_threshold": 23.5,
                "samples_collected": 20
            }
        },
        "thermal_data": {
            "version": "1.0",
            "state": {
                "current_state": "DRIFTING",
                "last_transition": "2025-08-08T15:45:00Z"
            },
            "model": {
                "tau_cooling": 95.5,
                "tau_warming": 148.2,
                "last_modified": "2025-08-08T15:30:00Z"
            },
            "probe_history": [
                {
                    "tau_value": 95.5,
                    "confidence": 0.85,
                    "duration": 3600,
                    "fit_quality": 0.92,
                    "aborted": False,
                    "timestamp": "2025-08-08T15:30:00Z"
                },
                {
                    "tau_value": 90.2,
                    "confidence": 0.78,
                    "duration": 2400,
                    "fit_quality": 0.88,
                    "aborted": False,
                    "timestamp": "2025-08-08T14:30:00Z"
                }
            ],
            "confidence": 0.75,
            "metadata": {
                "saves_count": 42,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }
        }
    }


# Empty thermal data for testing fresh starts
@pytest.fixture
def empty_thermal_data():
    """Empty thermal data structure for fresh ThermalManager instances."""
    return {
        "version": "1.0",
        "state": {
            "current_state": "PRIMING",
            "last_transition": "2025-08-08T16:00:00Z"
        },
        "model": {
            "tau_cooling": 90.0,
            "tau_warming": 150.0,
            "last_modified": "2025-08-08T16:00:00Z"
        },
        "probe_history": [],
        "confidence": 0.0,
        "metadata": {
            "saves_count": 0,
            "corruption_recoveries": 0,
            "schema_version": "1.0"
        }
    }


# Corrupted data scenarios for testing validation and recovery
@pytest.fixture
def corrupted_tau_values():
    """Corrupted thermal data with invalid tau values."""
    return {
        "version": "1.0",
        "state": {
            "current_state": "DRIFTING",
            "last_transition": "2025-08-08T15:45:00Z"
        },
        "model": {
            "tau_cooling": -50.0,  # Invalid negative value
            "tau_warming": 2000.0,  # Invalid too large value  
            "last_modified": "2025-08-08T15:30:00Z"
        },
        "probe_history": [],
        "confidence": 0.75,
        "metadata": {
            "saves_count": 10,
            "corruption_recoveries": 0,
            "schema_version": "1.0"
        }
    }


@pytest.fixture
def corrupted_thermal_state():
    """Corrupted thermal data with invalid state."""
    return {
        "version": "1.0", 
        "state": {
            "current_state": "INVALID_STATE",  # Invalid enum value
            "last_transition": "2025-08-08T15:45:00Z"
        },
        "model": {
            "tau_cooling": 95.5,
            "tau_warming": 148.2,
            "last_modified": "2025-08-08T15:30:00Z"
        },
        "probe_history": [],
        "confidence": 0.75,
        "metadata": {
            "saves_count": 10,
            "corruption_recoveries": 0,
            "schema_version": "1.0"
        }
    }


@pytest.fixture
def corrupted_probe_results():
    """Corrupted thermal data with invalid probe results."""
    return {
        "version": "1.0",
        "state": {
            "current_state": "DRIFTING",
            "last_transition": "2025-08-08T15:45:00Z"
        },
        "model": {
            "tau_cooling": 95.5,
            "tau_warming": 148.2,
            "last_modified": "2025-08-08T15:30:00Z"
        },
        "probe_history": [
            {
                "tau_value": -10.0,  # Invalid negative tau
                "confidence": 1.5,   # Invalid confidence > 1.0
                "duration": -300,    # Invalid negative duration
                "fit_quality": 2.0,  # Invalid fit_quality > 1.0
                "aborted": "maybe",  # Invalid non-boolean
                "timestamp": "invalid-date-format"  # Invalid timestamp
            },
            {
                "tau_value": "not_a_number",  # Invalid non-numeric tau
                "confidence": None,           # Invalid None confidence
                "duration": 0,                # Invalid zero duration
                "fit_quality": -0.5,         # Invalid negative fit_quality
                "aborted": True,
                "timestamp": "2025-08-08T14:30:00Z"
            }
        ],
        "confidence": 0.75,
        "metadata": {
            "saves_count": 10,
            "corruption_recoveries": 0,
            "schema_version": "1.0"
        }
    }


@pytest.fixture
def malformed_thermal_data():
    """Completely malformed thermal data for extreme corruption testing."""
    return {
        "version": "1.0",
        "state": "not_an_object",  # Should be object
        "model": ["should", "be", "object"],  # Should be object  
        "probe_history": "not_a_list",  # Should be list
        "confidence": "not_a_number",  # Should be float
        "metadata": 12345  # Should be object
    }


# ProbeResult test data generators
@pytest.fixture
def valid_probe_result_data():
    """Valid ProbeResult data structure."""
    return {
        "tau_value": 95.5,
        "confidence": 0.85,
        "duration": 3600,
        "fit_quality": 0.92,
        "aborted": False,
        "timestamp": "2025-08-08T15:30:00Z"
    }


@pytest.fixture
def probe_result_scenarios():
    """Various ProbeResult scenarios for testing."""
    return {
        "high_quality": {
            "tau_value": 95.5,
            "confidence": 0.95,
            "duration": 5400,
            "fit_quality": 0.98,
            "aborted": False,
            "timestamp": "2025-08-08T15:30:00Z"
        },
        "low_quality": {
            "tau_value": 88.2,
            "confidence": 0.45,
            "duration": 1800,
            "fit_quality": 0.65,
            "aborted": False,
            "timestamp": "2025-08-08T14:30:00Z"
        },
        "aborted": {
            "tau_value": 0.0,
            "confidence": 0.0,
            "duration": 600,
            "fit_quality": 0.0,
            "aborted": True,
            "timestamp": "2025-08-08T13:30:00Z"
        }
    }


# ThermalState test cases
@pytest.fixture
def thermal_state_scenarios():
    """Different ThermalState scenarios for testing."""
    return {
        "priming": {
            "current_state": "PRIMING",
            "expected_behavior": "Conservative bands, aggressive learning",
            "duration": "24-48 hours"
        },
        "drifting": {
            "current_state": "DRIFTING", 
            "expected_behavior": "AC off, passive drift, learning paused",
            "duration": "Variable"
        },
        "correcting": {
            "current_state": "CORRECTING",
            "expected_behavior": "AC on, boundary learning active",
            "duration": "Until boundary reached"
        },
        "recovery": {
            "current_state": "RECOVERY",
            "expected_behavior": "Gradual transition over 30-60min",
            "duration": "30-60 minutes"
        },
        "probing": {
            "current_state": "PROBING",
            "expected_behavior": "Active learning, ±2.0°C drift, notifications",
            "duration": "User controlled"
        },
        "calibrating": {
            "current_state": "CALIBRATING",
            "expected_behavior": "Daily 1-hour window, tight bands",
            "duration": "1 hour daily"
        }
    }


# Migration test scenarios
@pytest.fixture
def migration_scenarios():
    """Test scenarios for v1.0 to v2.1 data migration."""
    return {
        "simple_v1": {
            "input": {
                "version": "1.0",
                "entity_id": "climate.test",
                "last_updated": "2025-08-08T16:00:00Z",
                "learning_data": {"samples": 10, "accuracy": 0.8}
            },
            "expected_output": {
                "version": "2.1", 
                "entity_id": "climate.test",
                "last_updated": "2025-08-08T16:00:00Z",
                "learning_data": {"samples": 10, "accuracy": 0.8},
                "thermal_data": None
            }
        },
        "complex_v1": {
            "input": {
                "version": "1.0",
                "entity_id": "climate.complex",
                "last_updated": "2025-08-08T16:00:00Z",
                "learning_data": {
                    "samples": 50,
                    "accuracy": 0.9,
                    "hysteresis_data": {"threshold": 24.0}
                },
                "extra_field": "should_be_preserved"
            },
            "expected_output": {
                "version": "2.1",
                "entity_id": "climate.complex", 
                "last_updated": "2025-08-08T16:00:00Z",
                "learning_data": {
                    "samples": 50,
                    "accuracy": 0.9,
                    "hysteresis_data": {"threshold": 24.0}
                },
                "thermal_data": None,
                "extra_field": "should_be_preserved"
            }
        }
    }


# Helper fixtures for creating mock callbacks with specific behaviors
@pytest.fixture
def callback_test_helpers():
    """Helper functions for creating callbacks with specific behaviors."""
    def create_callback_returning_data(data):
        """Create a get_thermal_data callback that returns specific data."""
        callback = MagicMock()
        callback.return_value = data
        return callback
    
    def create_failing_callback(exception_msg="Callback failed"):
        """Create a callback that raises an exception."""
        callback = MagicMock()
        callback.side_effect = Exception(exception_msg)
        return callback
    
    def create_tracking_callback():
        """Create a callback that tracks all calls made to it."""
        callback = MagicMock()
        callback.call_history = []
        
        def track_calls(*args, **kwargs):
            callback.call_history.append({"args": args, "kwargs": kwargs})
            return None
        
        callback.side_effect = track_calls
        return callback
    
    return {
        "create_callback_returning_data": create_callback_returning_data,
        "create_failing_callback": create_failing_callback,
        "create_tracking_callback": create_tracking_callback
    }


# Tau value test ranges
@pytest.fixture
def tau_value_ranges():
    """Valid and invalid tau value ranges for testing validation."""
    return {
        "valid": {
            "tau_cooling": [1.0, 90.0, 150.0, 500.0, 1000.0],
            "tau_warming": [1.0, 90.0, 150.0, 500.0, 1000.0]
        },
        "invalid": {
            "too_small": [-10.0, -1.0, 0.0, 0.5],
            "too_large": [1001.0, 5000.0, 10000.0],
            "non_numeric": ["not_a_number", None, True, [], {}]
        }
    }


# Probe history test data with various lengths
@pytest.fixture
def probe_history_scenarios():
    """Probe history with different lengths for testing."""
    base_probe = {
        "tau_value": 95.0,
        "confidence": 0.85,
        "duration": 3600,
        "fit_quality": 0.92,
        "aborted": False,
        "timestamp": "2025-08-08T15:30:00Z"
    }
    
    return {
        "empty": [],
        "single": [base_probe],
        "partial": [base_probe] * 3,
        "full": [base_probe] * 5,
        "overfull": [base_probe] * 7  # Should truncate to 5
    }


# Complete thermal data factory for custom test scenarios
@pytest.fixture
def thermal_data_factory():
    """Factory function to create custom thermal data for specific test scenarios."""
    def create_thermal_data(
        current_state: str = "PRIMING",
        tau_cooling: float = 90.0,
        tau_warming: float = 150.0,
        probe_count: int = 0,
        confidence: float = 0.0,
        saves_count: int = 0,
        corruption_recoveries: int = 0
    ) -> Dict[str, Any]:
        """Create custom thermal data for testing."""
        probes = []
        if probe_count > 0:
            base_probe = {
                "tau_value": tau_cooling,
                "confidence": 0.85,
                "duration": 3600,
                "fit_quality": 0.92,
                "aborted": False,
                "timestamp": "2025-08-08T15:30:00Z"
            }
            probes = [base_probe] * min(probe_count, 5)  # Max 5 probes
        
        return {
            "version": "1.0",
            "state": {
                "current_state": current_state,
                "last_transition": "2025-08-08T16:00:00Z"
            },
            "model": {
                "tau_cooling": tau_cooling,
                "tau_warming": tau_warming,
                "last_modified": "2025-08-08T16:00:00Z"
            },
            "probe_history": probes,
            "confidence": confidence,
            "metadata": {
                "saves_count": saves_count,
                "corruption_recoveries": corruption_recoveries,
                "schema_version": "1.0"
            }
        }
    
    return create_thermal_data