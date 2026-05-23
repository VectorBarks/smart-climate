# Probe Scheduler and Learning Probes

Smart Climate has two probe concepts. Keep them separate:

1. **Thermal probes** measure room drift/correction behavior for the thermal model.
2. **Quiet Mode learning probes** deliberately nudge the wrapped AC setpoint to discover compressor hysteresis thresholds when natural data is missing.

Both are useful. Neither should be confused with natural compressor cycles.

## Probe Scheduler

The Probe Scheduler decides when active thermal calibration is allowed. Its goal is to gather useful thermal data without disrupting comfort or stressing equipment.

### Decision factors

- minimum time since last probe
- maximum interval since last useful calibration
- presence/calendar/manual override context when configured
- information gain from current outdoor/room conditions
- quiet hours and abort conditions
- current thermal state and compressor state

### Learning profiles

- **Comfort**: slower, conservative probing
- **Balanced**: default tradeoff between learning and comfort
- **Aggressive**: faster learning, more willing to probe
- **Custom**: advanced tuning for interval and information-gain thresholds

## Configuration keys

Most installs should use the Home Assistant options UI. YAML examples are shown for reference only.

```yaml
smart_climate:
  - name: Living Room Smart AC
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    power_sensor: sensor.living_room_ac_power
    probe_scheduler_enabled: true
    learning_profile: balanced
    presence_entity_id: binary_sensor.home_occupied
    weather_entity_id: weather.home
    calendar_entity_id: calendar.work
    manual_override_entity_id: input_boolean.allow_probe
    min_probe_interval_hours: 12
    max_probe_interval_days: 7
    information_gain_threshold: 0.5
```

## Quiet Mode learning probes

Quiet Mode normally suppresses avoidable setpoint commands. Before compressor thresholds are known, suppressing every idle-compressor command can prevent learning forever. To avoid that deadlock, Quiet Mode can allow a bounded learning probe.

Behavior:

- only when hysteresis thresholds are not known yet
- only when the compressor is idle
- bounded by the calculated target setpoint and `learning_probe_step`
- not sent while the compressor is already active
- transition result is stored as a **constraint**, not an exact natural sample

### Probe data semantics

Natural transition:

```text
start offset = room_temp_at_start - active_ac_setpoint
```

Probe transition:

```text
before offset = room_temp_at_transition - previous_ac_setpoint
after offset  = room_temp_at_transition - probed_ac_setpoint
threshold is somewhere between those values, or single-sided if only one side is known
```

Result: probe data narrows the plausible threshold range without polluting exact samples.

## When not to reset data

Do not reset just because a probe occurred. Probe constraints are expected and safe. Let the system continue collecting natural cycles.

Reset only after material physical changes, such as:

- AC replaced
- room sensor moved
- power sensor changed or power thresholds were badly wrong for a long time
- room layout/airflow changed substantially

## Useful diagnostics

On the climate entity and dashboard, check:

- `last_transition_cause`
- `last_transition_sample_type`
- `last_transition_offset_from_setpoint`
- `last_transition_offset_lower_bound`
- `last_transition_offset_upper_bound`
- `compressor_start_offset_lower_bound`
- `compressor_start_offset_upper_bound`
- `compressor_stop_offset_lower_bound`
- `compressor_stop_offset_upper_bound`
- `sensor.*_probing_active`
- `sensor.*_thermal_state`
- `sensor.*_quiet_mode_status`
