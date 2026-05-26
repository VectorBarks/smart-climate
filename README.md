# Smart Climate Control for Home Assistant

[![Version](https://img.shields.io/badge/Version-1.7.8--pre--release-orange.svg)](https://github.com/VectorBarks/smart-climate/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

Smart Climate Control wraps an existing Home Assistant climate entity and makes it behave like the room you actually care about, not like the AC unit's badly placed internal sensor.

Current pre-release: **v1.7.8**. This hotfix makes runtime setup honor Options Flow climate/room sensor overrides, so existing entries can be repointed without recreating Smart Climate or losing learning data.

## What it does

- Uses a trusted room temperature sensor as the source of truth.
- Sends corrected setpoints to the wrapped AC/heat-pump entity.
- Learns offset patterns from actual performance feedback.
- Uses power monitoring, when available, to detect compressor start/stop cycles.
- Learns setpoint-relative compressor hysteresis instead of relying on fragile absolute room-temperature thresholds.
- Treats deliberate learning probes as **bounds/constraints**, not exact natural samples.
- Supports Quiet Mode so the system avoids unnecessary beeps/commands while still allowing safe learning probes when thresholds are unknown.
- Provides thermal-state telemetry, probe status, cycle health, dashboard sensors, and a core-card Lovelace dashboard.

## Recommended setup

Minimum:
- Home Assistant 2024.1+
- Existing climate entity
- Room temperature sensor in the same room

Strongly recommended:
- Power sensor for the climate device, preferably a smart plug with live wattage
- Outdoor temperature sensor or weather entity
- Learning enabled after the basic entity is verified

## Installation

### HACS

1. HACS → Integrations → Custom repositories
2. Add `https://github.com/VectorBarks/smart-climate` as an **Integration**
3. Install **Smart Climate Control**
4. Restart Home Assistant
5. Settings → Devices & Services → Add Integration → Smart Climate Control

### Manual

Copy `custom_components/smart_climate` into your Home Assistant `custom_components/` directory, restart Home Assistant, then add the integration through the UI.

## Configuration

Use the Home Assistant UI. YAML remains useful for development and bulk setups, but normal installs should configure the integration through Settings → Devices & Services.

Required:
- climate entity
- room temperature sensor

Optional but important:
- outdoor sensor / weather entity for predictive and seasonal behavior
- power sensor for compressor-state and hysteresis learning
- Quiet Mode and learning probe step
- Probe Scheduler settings for thermal calibration

## Learning model

Smart Climate uses several layers:

1. **Reactive offset**: current room-vs-AC correction.
2. **Performance learning**: learns what offset worked after feedback delay.
3. **Compressor hysteresis**: with a power sensor, learns when the compressor naturally starts and stops.
4. **Probe constraints**: deliberate probes narrow threshold ranges without being counted as exact natural samples.
5. **Thermal model**: tracks room drift/correction behavior and calibration/probe state.

### Natural samples vs. probe constraints

Natural compressor transitions are high-quality samples:

```text
start offset = room_temp_at_start - active_ac_setpoint
stop offset  = room_temp_at_stop  - active_ac_setpoint
```

Learning probes are different. If Smart Climate nudges the AC setpoint to trigger a compressor transition, the result is only a boundary:

- a probe start proves the threshold is at or below the observed offset
- a probe stop proves the threshold is at or above the observed offset
- if both before/after setpoints are known, the threshold lies inside that interval

That is why probe data is useful without corrupting natural learning.

## Quiet Mode

Quiet Mode reduces unnecessary setpoint commands while still avoiding learning deadlocks:

- if thresholds are already known, Quiet Mode suppresses commands that would only make noise
- if thresholds are unknown and the compressor is idle, Smart Climate may send a bounded learning probe
- probes are not sent while the compressor is already active
- probe transitions are marked as constraints, not exact samples

## Dashboard

The dashboard service generates a robust Lovelace dashboard using only built-in Home Assistant cards. The generated dashboard now surfaces the full thermal recovery picture instead of hiding it behind one generic confidence number.

1. Developer Tools → Services
2. Call `smart_climate.generate_dashboard`
3. Select your Smart Climate entity
4. Copy the generated YAML from the notification into a dashboard raw editor

The dashboard uses real entity IDs from the entity registry. It does not depend on ApexCharts, Mushroom, Button Card, or placeholder replacement hacks.

What to look at after a reset or wrapped-climate outage:
- `sensor.{climate_name}_thermal_probe_confidence`: confidence from active thermal probes only
- `sensor.{climate_name}_passive_drift_confidence`: confidence from passive drift and safe Recorder backfill candidates
- `sensor.{climate_name}_overall_control_confidence`: control-facing combined confidence
- `sensor.{climate_name}_probe_diagnostics`: current scheduler mode, blocker, probe count, and next eligible probe time

If `thermal_probe_confidence` is still 0% but `passive_drift_confidence` and `overall_control_confidence` are useful, the system is not blind; it is using passive/history evidence while active probes rebuild.

## Documentation

- [Installation Guide](docs/installation-guide.md)
- [Configuration Guide](docs/configuration-guide.md)
- [User Guide](docs/user-guide.md)
- [Dashboard Setup](docs/dashboard-setup.md)
- [Sensor Reference](docs/sensor-reference.md)
- [Probe Scheduler Guide](docs/probe_scheduler.md)
- [Technical Reference](docs/technical-reference.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Services](docs/services.md)
- [Contributing](docs/contributing.md)

## Training data and reset guidance

Do **not** reset training data just because probes occurred. Probe transitions are now stored separately as constraints. Reset only when the physical setup materially changed, for example:

- AC unit replaced
- room sensor moved significantly
- power sensor changed or thresholds were badly wrong for a long period
- room layout/airflow changed enough to invalidate old data

For normal learning, let the system run. Natural cycles will improve accuracy over time.

## Support

- Issues: https://github.com/VectorBarks/smart-climate/issues
- Releases: https://github.com/VectorBarks/smart-climate/releases
- Documentation: [docs/](docs/)

## License

GPL-3.0. See [LICENSE](LICENSE).
