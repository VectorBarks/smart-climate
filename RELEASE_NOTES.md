# Release Notes

## v1.5.5-beta24 (2026-05-24)

### Summary
Runtime fallback values are now centralized instead of scattered through Smart Climate production code. A regression guard blocks the known hardcoded-value class that caused the previous `24.0°C` operating-window drift.

### Fixed
- Replaced hardcoded target-temperature fallbacks with `DEFAULT_TARGET_TEMPERATURE` / config lookups.
- Centralized thermal sensor fallback values for setpoint, outdoor/current temperature, comfort window, HVAC mode, and weather entity ID.
- Aligned the coordinator Quiet Mode default with `DEFAULT_QUIET_MODE_ENABLED`.
- Shared Quiet Mode supported HVAC modes between controller/analyzer code paths.

### Added
- `tests/test_no_runtime_magic_defaults.py` scanner guard for known unsafe runtime magic defaults.

### Verification
- `python -m py_compile custom_components/smart_climate/const.py custom_components/smart_climate/climate.py custom_components/smart_climate/thermal_sensor.py custom_components/smart_climate/thermal_manager.py custom_components/smart_climate/coordinator.py custom_components/smart_climate/quiet_mode_controller.py custom_components/smart_climate/compressor_state_analyzer.py custom_components/smart_climate/mode_manager.py custom_components/smart_climate/__init__.py custom_components/smart_climate/config_flow.py custom_components/smart_climate/migration.py`
- `pytest tests/test_no_runtime_magic_defaults.py tests/test_quiet_mode_controller.py tests/test_quiet_mode_coordinator_data.py tests/test_thermal_sensor.py tests/test_thermal_manager.py tests/test_target_temperature.py -q`
- `pytest tests/test_config_flow_power_options.py -q`
- Full `pytest -q` still blocked by existing collection/harness issues unrelated to this change: missing HA component mocks/packages, stale imports, and invalid legacy test character in `tests/test_climate_thermal_priority.py`.

## v1.5.5-beta23 (2026-05-24)

### Summary
Operating-window helper sensors now use the live Smart Climate target temperature instead of falling back to the historical 24.0°C default. Max Comfort windows stay centered on the configured room target.

### Fixed
- Replaced the hardcoded `24.0°C` operating-window setpoint fallback with the current Smart Climate climate-entity target.
- Removed hardcoded outdoor-temperature and HVAC-mode fallbacks from operating-window helper sensors.
- Return `unknown` instead of a plausible-but-wrong operating window when no real setpoint can be resolved.

### Verification
- `python -m py_compile custom_components/smart_climate/sensor_thermal.py tests/test_debug_entities_display.py`
- `pytest tests/test_debug_entities_display.py tests/test_quiet_mode_learning_mode_behavior.py tests/test_quiet_mode_config.py tests/test_quiet_mode_sensors.py tests/test_quiet_mode_controller.py tests/test_quiet_mode_e2e.py tests/test_quiet_mode_coordinator_data.py tests/test_quiet_mode_learning.py -q`

## v1.5.5-beta22 (2026-05-24)

### Summary
Power-correlation telemetry is now based on actual compressor transition events instead of fixed placeholder values. Dashboard labels now make learned/placeholder telemetry clearer.

### Added
- Transition-based power-correlation accuracy derived from observed compressor start/stop power deltas.
- Dashboard wording that distinguishes real learning telemetry from fallback/default values.

### Fixed
- Removed the fixed 85% power-correlation placeholder from the climate attribute path.
- Guarded learning telemetry attributes against non-numeric test/harness placeholder values.

### Verification
- `pytest tests/test_ac_learning_enhancement.py tests/test_runtime_dashboard_generator.py -q`
- `python -m py_compile custom_components/smart_climate/climate.py custom_components/smart_climate/dashboard/generator.py`
- `python - <<'PY'` + `yaml.safe_load('custom_components/smart_climate/dashboard/dashboard_generic.yaml')`

## v1.5.5-beta21 (2026-05-24)

### Summary
Fan-only power activity is now excluded from compressor hysteresis learning. Power changes while the wrapped climate entity is not in a learnable heating/cooling mode no longer create compressor start/stop samples.

### Fixed
- Ignored fan-only/off/dry power transitions for compressor hysteresis learning.
- Reset hysteresis transition baselines when entering non-learnable HVAC modes so stale cool/heat state cannot bridge into later samples.

### Verification
- `pytest tests/test_hysteresis_integration.py::TestHysteresisIntegration::test_fan_only_power_changes_are_ignored_for_hysteresis_learning tests/test_hysteresis_integration.py::TestHysteresisIntegration::test_power_transition_detection_start tests/test_hysteresis_integration.py::TestHysteresisIntegration::test_power_transition_detection_stop tests/test_quiet_mode_learning_mode_behavior.py tests/test_quiet_mode_learning.py -q`
- `python -m py_compile custom_components/smart_climate/offset_engine.py tests/test_hysteresis_integration.py`

## v1.5.5-beta20 (2026-05-23)

### Summary
Probe-induced compressor transitions are now data-safe. Quiet Mode learning probes narrow hysteresis thresholds as bounds/constraints instead of being promoted to exact natural start/stop samples.

### Added
- Setpoint-relative probe bounds for compressor start/stop learning.
- Persisted `start_probe_bounds` and `stop_probe_bounds` alongside natural offset samples.
- Diagnostic attributes for probe bounds and transition sample type.
- Dashboard visibility for compressor offsets, probe bounds, and latest transition semantics.

### Fixed
- Probe starts no longer corrupt learned natural hysteresis thresholds.
- Dashboard deployment now uses a robust core-card Lovelace dashboard with live entity IDs.

### Verification
- `python -m json.tool custom_components/smart_climate/manifest.json`
- `python -m py_compile custom_components/smart_climate/offset_engine.py custom_components/smart_climate/climate.py custom_components/smart_climate/compressor_state_analyzer.py custom_components/smart_climate/dashboard/generator.py tests/test_hysteresis_integration.py`
- `pytest tests/test_quiet_mode_learning_mode_behavior.py -q`
- focused hysteresis/probe regression tests in `tests/test_hysteresis_integration.py`

## v1.5.5-beta19 (2026-05-23)

### Summary
Learning probes are limited to idle-compressor conditions so active cooling cycles are not confused with threshold discovery.

### Fixed
- Prevented learning probes while the compressor is already active.
- Preserved normal Quiet Mode stepping behavior during active compressor operation.

## v1.5.5-beta17 (2026-05-23)

### Summary
Quiet Mode now actively learns compressor hysteresis instead of blocking itself. If thresholds are still unknown and cooling is requested while the compressor is idle, Smart Climate sends a safe progressive probe step toward the calculated AC setpoint.

### Added
- Progressive learning probes for unknown hysteresis thresholds: 0.5°C cooling steps, bounded by the calculated target setpoint.
- Explicit Quiet Mode reasons for learning probes, disabled mode, unsupported HVAC modes, active compressor, and threshold-crossing adjustments.

### Fixed
- Removed the learning deadlock where Quiet Mode suppressed idle-compressor adjustments while hysteresis thresholds were still unknown.

### Verification
- `pytest tests/test_quiet_mode_e2e.py tests/test_quiet_mode_controller.py tests/test_quiet_mode_learning.py tests/test_quiet_mode_learning_mode_behavior.py -q`
- `python -m compileall -q custom_components/smart_climate tests/test_quiet_mode_learning_mode_behavior.py tests/test_quiet_mode_controller.py tests/test_quiet_mode_learning.py tests/test_quiet_mode_e2e.py`

## v1.5.5-beta16 (2026-05-23)

### Summary
Dashboard generation is now rebuilt for real Home Assistant installs. The service no longer emits the old advanced template that guessed dozens of missing helper entity IDs and required custom Lovelace cards.

### Fixed
- Dashboard service now discovers related Smart Climate entities from the live entity registry/config entry.
- Generated dashboards reference only entities that exist in Home Assistant for the selected climate entity.
- Generated dashboards use only built-in Home Assistant cards: thermostat, markdown, gauge, entities, and history-graph.

### Verification
- Runtime dashboard generated for `climate.smart_klimaanlage_tu_climate` referenced 52 entities with 0 missing entity IDs.

## v1.5.5-beta15 (2026-05-23)

### Summary
The main `Smart Klimaanlage TU Climate` entity now uses explicit diagnostic states instead of ambiguous `None`/`Unknown` attributes.

### Fixed
- `predictive_strategy` now reports `disabled`, `no_active_strategy`, or `error` when no active strategy dict exists.
- `temperature_window_learned` now reports `learning`, `disabled`, `not_available`, or `error` instead of `Unknown`.

### Added
- `predictive_strategy_status_detail` and `predictive_strategy_source` attributes.
- `temperature_window_status_detail` and `temperature_window_source` attributes.

## v1.5.5-beta14 (2026-05-23)

### Summary
Finishes the diagnostic polish pass by adding explanatory detail attributes for convergence, Quiet Mode, suppressions, and compressor state.

### Added
- `status_detail` and `source` attributes for `sensor.*_convergence_trend`.
- `status_detail` and `source` attributes for `sensor.*_quiet_mode_status`, `sensor.*_quiet_mode_suppressions`, and `sensor.*_compressor_state`.

## v1.5.5-beta13 (2026-05-23)

### Summary
Diagnostic/debug entities now render explicit states instead of persistent `unknown`, and their attributes explain whether a value is active, disabled, still learning, or waiting for cycle/probe history.

### Fixed
- `sensor.*_weather_forecast` and `sensor.*_seasonal_adaptation` now show `enabled`/`disabled` on the sensor platform.
- `sensor.*_convergence_trend` accepts live `learning` and `not_learning` states.
- `sensor.*_temperature_window` now shows `learning`/`disabled` instead of `unknown` while hysteresis data is incomplete.
- `sensor.*_shadow_mode`, `sensor.*_probing_active`, and `sensor.*_cycle_health` now publish sensor states instead of relying on binary-sensor-only APIs.
- `sensor.*_average_on_cycle` and `sensor.*_average_off_cycle` read the wired `CycleMonitor` tuple API.

### Added
- Entity-detail attributes such as `status_detail`, `source`, sample counts, cycle counts, and seasonal context to make the debug entities self-explaining.
- Focused regression tests for diagnostic display states.

## v1.5.5-beta12 (2026-05-23)

### Summary
Quiet Mode dashboard sensors now receive live data on the actual dashboard sensor coordinator path instead of staying `unknown`, including the matching Smart Climate suppression count.

### Fixed
- `sensor.*_compressor_state` now reports `idle` or `active` from the configured AC power sensor and idle threshold.
- `sensor.*_quiet_mode_status` now reports enabled/disabled coordinator state.
- `sensor.*_quiet_mode_suppressions` now mirrors the live Quiet Mode controller suppression count.
- Dict-backed dashboard coordinator payloads are read correctly by the Quiet Mode sensor entities.
- Suppression lookup follows the Smart Climate entity associated with the wrapped source climate entity.

### Validation
- Added focused regression coverage for real `SmartClimateData`, dashboard data augmentation, and dict-backed Quiet Mode sensor payloads.
- Verified focused tests and Python compile checks locally before release.

## v1.5.5-beta9 (2026-05-23)

### Summary
Smart Climate now hydrates diagnostic polling sensors during setup/reload, so humidity-derived entities publish useful values immediately instead of staying `unknown` until the next scheduled update.

### User Impact
- Humidity and derived diagnostic sensors become available immediately after Home Assistant reload/setup.
- Dashboards stop showing stale `unknown` states for the affected Smart Climate sensors after reload.
- No user configuration change required.

### Fixed
- `sensor.smart_climate_indoor_humidity`
- `sensor.smart_climate_outdoor_humidity`
- `sensor.smart_climate_humidity_differential`
- `sensor.smart_climate_heat_index`
- `sensor.smart_climate_dew_point_indoor`
- `sensor.smart_climate_absolute_humidity`

### Validation
- Added a focused regression test for Home Assistant's `async_add_entities(..., True)` initial-update contract.
- Verified the fix against a live Home Assistant reload with Smart Climate `v1.5.5-beta9`.

## Document Policy
- `README.md`: project overview, installation, and user-facing docs.
- `CHANGELOG.md`: complete chronological history for maintainers.
- `RELEASE_NOTES.md`: concise user-facing notes for the current/latest release.
