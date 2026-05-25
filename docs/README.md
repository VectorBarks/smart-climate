# Smart Climate Control Documentation

Documentation for Smart Climate Control, a Home Assistant custom integration that wraps an existing climate entity and adds room-sensor based offset control, learning, compressor-state awareness, Quiet Mode, thermal telemetry, and dashboard tooling.

Current docs target **v1.6.0**.

## Start here

- [Installation Guide](installation-guide.md) — HACS/manual install, updates, migration notes
- [Configuration Guide](configuration-guide.md) — UI settings, YAML examples, thresholds, learning options
- [User Guide](user-guide.md) — daily operation, learning behavior, reset guidance
- [Dashboard Setup](dashboard-setup.md) — generate and use the core-card dashboard
- [Troubleshooting](troubleshooting.md) — common operational issues

## Feature references

- [Sensor Reference](sensor-reference.md) — dashboard and diagnostic entities
- [Probe Scheduler Guide](probe_scheduler.md) — thermal calibration scheduling and probe safety
- [Technical Reference](technical-reference.md) — architecture and algorithms
- [Services](services.md) — integration services

## Current behavior summary

### Learning

- Basic offset learning works with any supported climate entity and room sensor.
- Power-sensor installs additionally learn compressor start/stop behavior.
- Hysteresis is modeled relative to the active AC setpoint, not as fixed absolute room temperatures.
- Natural compressor transitions are exact samples.
- Deliberate learning probes are stored as bounds/constraints so calibration does not poison the natural dataset.

### Quiet Mode

- Quiet Mode suppresses avoidable noisy setpoint commands.
- When thresholds are unknown, it can allow bounded learning probes instead of deadlocking learning.
- Probes are blocked while the compressor is active.

### Dashboard

- The generated dashboard uses only built-in Home Assistant cards.
- It references live entities discovered from the entity registry.
- It does not require ApexCharts or other custom Lovelace cards.
- It should not contain `REPLACE_ME` placeholders.

## Requirements

- Home Assistant 2024.1+
- Python 3.11+
- Existing climate entity
- Room temperature sensor
- Optional but recommended: outdoor sensor/weather entity and power sensor

## Maintenance policy

- `README.md`: concise user-facing overview.
- `docs/`: focused how-to and reference docs.
- `CHANGELOG.md`: historical release history; old entries are preserved.
- `RELEASE_NOTES.md`: current/latest user-facing release notes.
