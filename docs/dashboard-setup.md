# Dashboard Setup Guide

Smart Climate Control can generate a Lovelace dashboard for a selected Smart Climate entity. The current dashboard is intentionally conservative: it uses only built-in Home Assistant cards and live entity IDs discovered from the entity registry.

## What the generated dashboard includes

- **Overview**: thermostat card, live status, current offsets, compressor/probe status
- **Learning**: learning, calibration, hysteresis, probe, sample, and forecast-related entities
- **Thermal**: thermal state, compressor/cycle metrics, comfort/window data
- **Performance**: accuracy, offset, model, prediction, correlation, efficiency, and latency metrics
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

## Related docs

- [User Guide](user-guide.md)
- [Sensor Reference](sensor-reference.md)
- [Technical Reference](technical-reference.md#ac-temperature-window-detection-hysteresislearner)
