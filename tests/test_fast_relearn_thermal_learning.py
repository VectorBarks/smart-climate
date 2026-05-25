"""Regression tests for accelerated Smart Climate thermal relearning."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from custom_components.smart_climate.const import (
    DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD,
    DEFAULT_PASSIVE_MIN_DRIFT_MINUTES,
    DOMAIN,
)
from custom_components.smart_climate.probe_scheduler import ProbeScheduler, LearningProfile
from custom_components.smart_climate.thermal_history_backfill import build_probe_results_from_history
from custom_components.smart_climate.thermal_model import PassiveThermalModel, ProbeResult


def _hass_with_states(states=None):
    hass = Mock()
    hass.data = {DOMAIN: {}}
    hass.states = Mock()
    states = states or {}
    hass.states.get.side_effect = lambda entity_id: states.get(entity_id)
    return hass


def _probe(hours_ago: float, source: str = "active", outdoor_temp: float = 22.0) -> ProbeResult:
    return ProbeResult(
        tau_value=900.0,
        confidence=0.8,
        duration=900,
        fit_quality=0.9,
        aborted=False,
        timestamp=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
        outdoor_temp=outdoor_temp,
        source=source,
    )


def test_first_probe_is_prioritized_and_reports_diagnostic_reason():
    model = PassiveThermalModel()
    model._probe_history.clear()
    scheduler = ProbeScheduler(
        hass=_hass_with_states(),
        thermal_model=model,
        presence_entity_id="person.vector",
        weather_entity_id=None,
        learning_profile=LearningProfile.BALANCED,
    )

    assert scheduler.should_probe_now() is True

    diagnostics = scheduler.get_probe_diagnostics()
    assert diagnostics["last_decision"] == "approved"
    assert diagnostics["last_blocker"] == "approved_first_probe"
    assert diagnostics["fast_relearn_active"] is True
    assert diagnostics["probe_count"] == 0


def test_fast_relearn_uses_six_hour_interval_and_skips_presence_block():
    model = PassiveThermalModel()
    model._probe_history.clear()
    model.add_probe_result(_probe(hours_ago=7))
    scheduler = ProbeScheduler(
        hass=_hass_with_states({"person.vector": Mock(state="on", attributes={})}),
        thermal_model=model,
        presence_entity_id="person.vector",
        weather_entity_id=None,
        learning_profile=LearningProfile.COMFORT,
    )

    assert scheduler.should_probe_now() is True

    diagnostics = scheduler.get_probe_diagnostics()
    assert diagnostics["mode"] == "fast_relearn"
    assert diagnostics["effective_min_interval_hours"] == 6
    assert diagnostics["presence_check_skipped"] is True


def test_normal_learning_reports_min_interval_blocker_and_next_eligible_time():
    model = PassiveThermalModel()
    model._probe_history.clear()
    for index in range(5):
        model.add_probe_result(_probe(hours_ago=1 + index, outdoor_temp=15.0 + index))
    scheduler = ProbeScheduler(
        hass=_hass_with_states(),
        thermal_model=model,
        presence_entity_id=None,
        weather_entity_id=None,
        learning_profile=LearningProfile.BALANCED,
    )

    assert scheduler.should_probe_now() is False

    diagnostics = scheduler.get_probe_diagnostics()
    assert diagnostics["fast_relearn_active"] is False
    assert diagnostics["last_blocker"] == "blocked_min_interval"
    assert diagnostics["eligible_next_probe_at"] is not None
    assert diagnostics["hours_until_next_probe"] > 0


def test_confidence_breakdown_separates_active_passive_and_backfill_sources():
    model = PassiveThermalModel()
    model._probe_history.clear()
    model.add_probe_result(_probe(hours_ago=12, source="active", outdoor_temp=20.0))
    model.add_probe_result(_probe(hours_ago=8, source="passive", outdoor_temp=21.0))
    model.add_probe_result(_probe(hours_ago=4, source="history_backfill", outdoor_temp=22.0))

    breakdown = model.get_confidence_breakdown()

    assert breakdown["thermal_probe_confidence"] > 0
    assert breakdown["passive_drift_confidence"] > 0
    assert breakdown["overall_model_confidence"] >= breakdown["thermal_probe_confidence"]
    assert breakdown["active_probe_count"] == 1
    assert breakdown["passive_probe_count"] == 2


def test_history_backfill_builds_passive_probe_candidates_from_recorder_samples():
    now = datetime.now(timezone.utc)
    samples = []
    # one earlier active sample, then a 30 minute passive/off drift window
    samples.append({"timestamp": now - timedelta(minutes=35), "room_temp": 24.0, "outdoor_temp": 29.0, "hvac_mode": "cool"})
    for idx in range(7):
        samples.append({
            "timestamp": now - timedelta(minutes=30 - idx * 5),
            "room_temp": 24.0 + idx * 0.12,
            "outdoor_temp": 29.0,
            "hvac_mode": "off",
        })

    probes = build_probe_results_from_history(samples, min_duration_minutes=10)

    assert len(probes) == 1
    assert probes[0].source == "history_backfill"
    assert probes[0].confidence >= DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD
    assert probes[0].duration >= 600


def test_passive_learning_defaults_are_aggressive_enough_for_relearn():
    assert DEFAULT_PASSIVE_MIN_DRIFT_MINUTES == 10
    assert DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD == 0.2
