# Dashboard Setup Guide

Smart Climate Control can generate a Lovelace dashboard for a selected Smart Climate entity. The current dashboard is intentionally conservative: it uses only built-in Home Assistant cards and live entity IDs discovered from the entity registry.

## What the generated dashboard includes

- **Overview**: thermostat card, live status, current offsets, compressor/probe status, thermal relearn explanation, and confidence gauges
- **Learning**: learning, calibration, hysteresis, probe, sample, and forecast-related entities
- **Thermal**: thermal state, compressor/cycle metrics, comfort/window data, probe diagnostics, fast-relearn status, and confidence breakdown
- **Performance**: accuracy, offset, model, prediction, correlation, confidence, efficiency, and latency metrics
- **Diagnostics**: broad list of related Smart Climate entities for debugging

## Why this replaced the old dashboard

Older dashboard templates guessed entity IDs and referenced custom Lovelace cards. Real Home Assistant installs can rename entities, use different prefixes, or not have those custom cards installed. The current generator avoids that trap:

- no guessed helper entity IDs
- no `REPLACE_ME_*` placeholders
- no ApexCharts/Mushroom/Button Card dependency
- only entities attached to the selected Smart Climate config entry
- only core Home Assistant card types

## Generate a dashboard

1. Open **Developer Tools → Services**.
2. Select `smart_climate.generate_dashboard`.
3. Choose your Smart Climate climate entity, for example `climate.living_room_smart_ac`.
4. Click **Call Service**.
5. Open the persistent notification created by Home Assistant.
6. Copy the YAML block.
7. Create or edit a Lovelace dashboard and paste it into the raw configuration editor.
8. Save.

Example service call:

```yaml
service: smart_climate.generate_dashboard
data:
  climate_entity_id: climate.living_room_smart_ac
```

## Hysteresis and probe fields shown in the dashboard

The Overview markdown card exposes the important learning distinction:

- `compressor_start_offset` / `compressor_stop_offset`: learned natural exact offsets when enough natural data exists
- `compressor_start_offset_lower_bound` / `compressor_start_offset_upper_bound`: bounds learned from start probes
- `compressor_stop_offset_lower_bound` / `compressor_stop_offset_upper_bound`: bounds learned from stop probes
- `last_transition_cause`: `natural`, `probe`, or other diagnostic cause
- `last_transition_sample_type`: `exact`, `constraint`, or `ignored`
- `last_transition_offset_lower_bound` / `last_transition_offset_upper_bound`: latest probe interval or single-sided bound

This is the main data-quality safeguard: probe events help narrow thresholds but do not count as exact natural samples.

## Thermal relearn and confidence fields shown in the dashboard

The generated dashboard includes a **Thermal relearn confidence** markdown card plus dedicated gauges when the related sensors exist. This is the recovery view to use after a reset, HA reload, wrapped-climate outage, or lost thermal probe history.

- `sensor.{climate_name}_thermal_state`: current thermal phase such as `priming`, `drifting`, `probing`, or `correcting`
- `sensor.{climate_name}_model_confidence`: legacy headline confidence; attributes also expose the active/passive split when available
- `sensor.{climate_name}_thermal_probe_confidence`: confidence from active thermal probes only
- `sensor.{climate_name}_passive_drift_confidence`: confidence from passive drift and safe Recorder-history backfill candidates
- `sensor.{climate_name}_overall_control_confidence`: control-facing confidence that combines active probes and passive drift evidence
- `sensor.{climate_name}_probe_diagnostics`: latest probe scheduler decision, mode, blocker, probe count, effective interval, and next eligible probe time

How to read the common recovery states:

- `fast_relearn`: commissioning/recovery mode. The first five probes use shorter safe intervals so relearning does not take days.
- `approved_first_probe`: empty probe history is not waiting for perfect diversity; the first valid recovery probe is allowed.
- `blocked_min_interval`: not a failure. The scheduler is intentionally waiting until the next safe probe time.
- `thermal_probe_confidence = 0%` with useful passive/overall confidence: active probes are still young, but passive/history evidence is already supporting control.

Do not reset training data just because the dashboard shows `blocked_min_interval` or 0% active probe confidence. Use `probe_diagnostics` to see whether the system is waiting intentionally or truly blocked.

## Customizing after generation

The generated dashboard is meant to be a safe baseline. You can still edit it in Lovelace:

- rename cards
- move cards between tabs
- add custom graphs if you already use custom cards
- add other room or energy entities

If you install custom cards later, add them manually. The generator deliberately stays dependency-free.

## Troubleshooting

### Service call succeeds but no dashboard appears

The service creates a notification containing YAML. It does not automatically create a dashboard tab. Open persistent notifications and copy the YAML into a dashboard.

### Dashboard has missing entities

Regenerate it after the integration is fully loaded. The generator only includes entities that exist in the Home Assistant entity registry for the selected config entry.

### Dashboard still contains placeholders

That is stale YAML from the old template. Regenerate the dashboard with the current integration version and replace the old raw configuration.

### Some entities show `unavailable` or `learning`

That can be normal during startup or early learning. Check the status/detail attributes on the entity for the reason.

### Thermal probe confidence is 0% but overall confidence is not

That is expected after cold-start recovery. Active thermal probes need real probe history, while passive drift and Recorder backfill can already contribute to `overall_control_confidence`. Watch `probe_diagnostics` for `fast_relearn`, `probe_count`, and `eligible_next_probe_at` before assuming the model is stuck.

## Related docs

- [User Guide](user-guide.md)
- [Sensor Reference](sensor-reference.md)
- [Technical Reference](technical-reference.md#ac-temperature-window-detection-hysteresislearner)
