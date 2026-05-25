"""Recorder-history backfill for Smart Climate thermal learning.

Builds conservative passive ProbeResult candidates from Home Assistant history when
thermal probe history is empty after a reset/reload. All operations are best-effort:
missing recorder/history data must never block integration startup.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_OUTDOOR_SENSOR,
    CONF_POWER_IDLE_THRESHOLD,
    CONF_POWER_SENSOR,
    CONF_ROOM_SENSOR,
    DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD,
    DEFAULT_PASSIVE_MIN_DRIFT_MINUTES,
    DEFAULT_POWER_IDLE_THRESHOLD,
)
from .thermal_model import PassiveThermalModel, ProbeResult

_LOGGER = logging.getLogger(__name__)

_PASSIVE_HVAC_STATES = {"off", "idle", "fan_only"}
_ACTIVE_HVAC_STATES = {"cool", "heat", "heat_cool", "auto", "dry"}


def _as_timestamp(value: Any) -> Optional[float]:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = getattr(value, "last_changed", None) or getattr(value, "last_updated", None)
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _as_float(value: Any) -> Optional[float]:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_passive_sample(sample: dict[str, Any]) -> bool:
    hvac_mode = str(sample.get("hvac_mode") or "").lower()
    compressor_active = sample.get("compressor_active")
    if compressor_active is False:
        return True
    if compressor_active is True:
        return False
    return hvac_mode in _PASSIVE_HVAC_STATES


def _segment_to_probe(segment: list[dict[str, Any]], min_duration_minutes: int) -> Optional[ProbeResult]:
    if len(segment) < 3:
        return None

    first_ts = float(segment[0]["timestamp"])
    last_ts = float(segment[-1]["timestamp"])
    duration = last_ts - first_ts
    if duration < min_duration_minutes * 60:
        return None

    temps = [_as_float(sample.get("room_temp")) for sample in segment]
    temps = [temp for temp in temps if temp is not None]
    if len(temps) < 3:
        return None

    drift = abs(temps[-1] - temps[0])
    if drift < 0.2:
        return None

    outdoor_values = [_as_float(sample.get("outdoor_temp")) for sample in segment]
    outdoor_values = [temp for temp in outdoor_values if temp is not None]
    outdoor_temp = sum(outdoor_values) / len(outdoor_values) if outdoor_values else None

    # Prefer the proper curve fit when scipy can fit the sample; fall back to a
    # conservative seed so reset recovery still gets a useful starting point.
    try:
        from .thermal_utils import analyze_drift_data
        drift_data = [(float(sample["timestamp"]), float(sample["room_temp"])) for sample in segment]
        fitted = analyze_drift_data(drift_data, is_passive=True, outdoor_temp=outdoor_temp)
        if fitted and fitted.confidence >= DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD:
            return ProbeResult(
                tau_value=fitted.tau_value,
                confidence=fitted.confidence,
                duration=fitted.duration,
                fit_quality=fitted.fit_quality,
                aborted=False,
                timestamp=datetime.fromtimestamp(last_ts, timezone.utc),
                outdoor_temp=outdoor_temp,
                source="history_backfill",
            )
    except Exception as exc:  # pragma: no cover - defensive against optional scipy/recorder quirks
        _LOGGER.debug("History backfill curve fit failed, using fallback seed: %s", exc)

    duration_factor = min(duration / (60 * 60), 1.0)
    drift_factor = min(drift / 1.0, 1.0)
    confidence = max(DEFAULT_PASSIVE_CONFIDENCE_THRESHOLD, min(0.55, 0.2 + 0.2 * duration_factor + 0.15 * drift_factor))
    fit_quality = max(0.3, min(0.8, 0.4 + 0.2 * drift_factor))
    tau_value = max(300.0, min(86400.0, duration / 3.0))
    return ProbeResult(
        tau_value=tau_value,
        confidence=confidence,
        duration=int(duration),
        fit_quality=fit_quality,
        aborted=False,
        timestamp=datetime.fromtimestamp(last_ts, timezone.utc),
        outdoor_temp=outdoor_temp,
        source="history_backfill",
    )


def build_probe_results_from_history(
    samples: Iterable[dict[str, Any]],
    *,
    min_duration_minutes: int = DEFAULT_PASSIVE_MIN_DRIFT_MINUTES,
    max_probes: int = 3,
) -> list[ProbeResult]:
    """Build passive probe candidates from normalized Recorder samples.

    Samples must contain timestamp, room_temp, and either hvac_mode or
    compressor_active. Timestamps may be datetime or Unix seconds.
    """
    normalized: list[dict[str, Any]] = []
    for sample in samples:
        ts = sample.get("timestamp")
        if isinstance(ts, datetime):
            timestamp = ts.timestamp()
        else:
            timestamp = _as_float(ts)
        room_temp = _as_float(sample.get("room_temp"))
        if timestamp is None or room_temp is None:
            continue
        normalized.append({**sample, "timestamp": timestamp, "room_temp": room_temp})

    normalized.sort(key=lambda item: item["timestamp"])
    probes: list[ProbeResult] = []
    current_segment: list[dict[str, Any]] = []
    previous_was_active = False

    for sample in normalized:
        passive = _is_passive_sample(sample)
        hvac_mode = str(sample.get("hvac_mode") or "").lower()
        active = hvac_mode in _ACTIVE_HVAC_STATES or sample.get("compressor_active") is True

        if passive:
            if not current_segment and not previous_was_active:
                # Still allow backfill when history begins inside an off window.
                current_segment = []
            current_segment.append(sample)
        else:
            if current_segment:
                probe = _segment_to_probe(current_segment, min_duration_minutes)
                if probe:
                    probes.append(probe)
            current_segment = []
            previous_was_active = active

    if current_segment:
        probe = _segment_to_probe(current_segment, min_duration_minutes)
        if probe:
            probes.append(probe)

    # newest first would bias toward current building behavior; keep chronological
    # but cap to avoid overfilling model with inferred data.
    return probes[-max_probes:]


def _state_to_float(state: Any) -> Optional[float]:
    return _as_float(getattr(state, "state", None))


def _value_at(states: list[Any], timestamp: float) -> Optional[Any]:
    latest = None
    latest_ts = None
    for state in states:
        state_ts = _as_timestamp(state)
        if state_ts is None or state_ts > timestamp:
            continue
        if latest_ts is None or state_ts >= latest_ts:
            latest = state
            latest_ts = state_ts
    return latest


async def async_backfill_from_recorder(
    hass: Any,
    thermal_model: PassiveThermalModel,
    config: dict[str, Any],
    *,
    lookback_hours: int = 48,
    max_probes: int = 3,
) -> int:
    """Backfill empty thermal history from Home Assistant Recorder history.

    Returns the number of added probes. Fails closed with 0 on recorder/history
    issues so integration startup is never blocked.
    """
    if thermal_model.get_probe_count() > 0:
        return 0

    entity_ids = [
        config.get(CONF_ROOM_SENSOR),
        config.get(CONF_CLIMATE_ENTITY),
        config.get(CONF_OUTDOOR_SENSOR),
        config.get(CONF_POWER_SENSOR),
    ]
    entity_ids = [entity_id for entity_id in entity_ids if entity_id]
    if len(entity_ids) < 2:
        return 0

    try:
        from homeassistant.components.recorder import history
        from homeassistant.util import dt as dt_util
    except Exception as exc:
        _LOGGER.debug("Recorder history unavailable for thermal backfill: %s", exc)
        return 0

    end_time = dt_util.utcnow()
    start_time = end_time - timedelta(hours=lookback_hours)

    def _read_history():
        try:
            return history.get_significant_states(
                hass,
                start_time,
                end_time,
                entity_ids,
                minimal_response=False,
                no_attributes=False,
            )
        except TypeError:
            return history.get_significant_states(hass, start_time, end_time, entity_ids)

    try:
        raw = await hass.async_add_executor_job(_read_history)
    except Exception as exc:
        _LOGGER.debug("Thermal backfill recorder query failed: %s", exc)
        return 0

    room_states = raw.get(config.get(CONF_ROOM_SENSOR), []) if isinstance(raw, dict) else []
    climate_states = raw.get(config.get(CONF_CLIMATE_ENTITY), []) if isinstance(raw, dict) else []
    outdoor_states = raw.get(config.get(CONF_OUTDOOR_SENSOR), []) if isinstance(raw, dict) else []
    power_states = raw.get(config.get(CONF_POWER_SENSOR), []) if isinstance(raw, dict) else []

    idle_threshold = float(config.get(CONF_POWER_IDLE_THRESHOLD, DEFAULT_POWER_IDLE_THRESHOLD))
    samples: list[dict[str, Any]] = []
    for room_state in room_states:
        ts = _as_timestamp(room_state)
        room_temp = _state_to_float(room_state)
        if ts is None or room_temp is None:
            continue
        climate_state = _value_at(climate_states, ts)
        outdoor_state = _value_at(outdoor_states, ts)
        power_state = _value_at(power_states, ts)
        power = _state_to_float(power_state) if power_state is not None else None
        samples.append({
            "timestamp": ts,
            "room_temp": room_temp,
            "outdoor_temp": _state_to_float(outdoor_state) if outdoor_state is not None else None,
            "hvac_mode": getattr(climate_state, "state", None) if climate_state is not None else None,
            "compressor_active": (power >= idle_threshold) if power is not None else None,
        })

    probes = build_probe_results_from_history(
        samples,
        min_duration_minutes=int(config.get("passive_min_drift_minutes", DEFAULT_PASSIVE_MIN_DRIFT_MINUTES)),
        max_probes=max_probes,
    )
    for probe in probes:
        thermal_model.update_tau(probe, is_cooling=True)

    if probes:
        _LOGGER.info("Thermal history backfill added %d passive probe candidates", len(probes))
    return len(probes)
