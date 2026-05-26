# Release Notes

## v1.7.6

Hotfix for ARGO/CMK entity replacement without losing Smart Climate learned data.

### Fixed
- Expose the wrapped `climate_entity` in the Options Flow so an existing Smart Climate entry can be pointed at a replacement physical climate entity.
- Pass the existing config entry into the Options Flow so current config data is available as defaults.

### Verified
- `pytest tests/test_config_flow_power_options.py tests/test_config_flow_climate_entity_options.py -q`
- `python -m py_compile custom_components/smart_climate/config_flow.py custom_components/smart_climate/__init__.py`
- `python -m json.tool custom_components/smart_climate/manifest.json >/dev/null`


## v1.7.5 (2026-05-25)

### Added
- Generated runtime dashboards now include a **Thermal relearn confidence** explanation card with live states for thermal state, model confidence, active thermal probe confidence, passive drift/backfill confidence, overall control confidence, and probe diagnostics.
- Dedicated dashboard gauges for `thermal_probe_confidence`, `passive_drift_confidence`, `overall_control_confidence`, and `model_confidence` when those entities exist.
- Probe scheduler explanation card that documents `approved_first_probe`, `fast_relearn`, and `blocked_min_interval` directly in the generated dashboard.

### Documentation
- README, dashboard setup, sensor reference, technical reference, troubleshooting, and service docs now describe the confidence split, fast-relearn recovery, Recorder-history backfill, and probe diagnostics.

## v1.7.4 (2026-05-25)

### Summary
Smart Climate Control v1.7.4 is a pre-release focused on thermal cold-start recovery after data loss, reset, or wrapped ARGO climate churn. It adds faster relearning, recorder-history backfill, split confidence telemetry, and explicit probe-blocker diagnostics.

### Added
- Fast-relearn / commissioning mode for the first five thermal probes: first chance is prioritized, minimum interval drops to 6 hours, maximum interval drops to 48 hours, and presence blocking is skipped during relearn.
- Recorder-history backfill that infers conservative passive probe candidates from room temperature, outdoor temperature, HVAC mode, and power/compressor history when probe history is empty.
- Split confidence telemetry for active thermal probes, passive/history drift, and overall control confidence.
- `Probe Diagnostics` sensor attributes exposing the latest scheduling decision, blocker reason, next eligible probe time, effective mode, and relearn status.

### Changed
- Passive drift learning defaults are more useful after reset: minimum drift window is now 10 minutes and confidence threshold is now 0.2.
- Empty probe-history cold starts now prioritize the first valid probe instead of waiting for perfect diversity/opportunity.
- Thermal persistence keeps probe source metadata (`active`, `passive`, `history_backfill`) for clearer diagnostics.
- `analyze_drift_data` now has a NumPy-only fallback so passive/history learning still works when SciPy is unavailable.
- README/HACS metadata now points at the current pre-release train.

### Verification
- `python -m json.tool custom_components/smart_climate/manifest.json >/dev/null && python -m json.tool hacs.json >/dev/null`
- `python -m py_compile custom_components/smart_climate/probe_scheduler.py custom_components/smart_climate/thermal_model.py custom_components/smart_climate/thermal_models.py custom_components/smart_climate/thermal_utils.py custom_components/smart_climate/thermal_manager.py custom_components/smart_climate/thermal_history_backfill.py custom_components/smart_climate/sensor_thermal.py custom_components/smart_climate/sensor.py custom_components/smart_climate/__init__.py`
- `python -m pytest tests/test_fast_relearn_thermal_learning.py tests/test_thermal_utils.py tests/test_probe_scheduler_edge_cases.py::TestProbeSchedulerEdgeCases::test_empty_probe_history_scenarios -q`
- Full `python -m pytest -q` is still blocked at collection by existing local HA test-harness/legacy issues unrelated to this change: missing mocked HA button/switch/weather/setup packages, missing optional `freezegun`/`pytest_homeassistant_custom_component`, stale removed config constants/imports, non-subscriptable mocked `DataUpdateCoordinator`, and an invalid legacy U+200C character in `tests/test_climate_thermal_priority.py`.

## v1.7.3 (2026-05-25)

### Summary
Smart Climate Control v1.7.3 is a pre-release focused on thermal cold-start recovery after data loss, reset, or wrapped ARGO climate churn. It adds faster relearning, recorder-history backfill, split confidence telemetry, and explicit probe-blocker diagnostics.

### Added
- Fast-relearn / commissioning mode for the first five thermal probes: first chance is prioritized, minimum interval drops to 6 hours, maximum interval drops to 48 hours, and presence blocking is skipped during relearn.
- Recorder-history backfill that infers conservative passive probe candidates from room temperature, outdoor temperature, HVAC mode, and power/compressor history when probe history is empty.
- Split confidence telemetry for active thermal probes, passive/history drift, and overall control confidence.
- `Probe Diagnostics` sensor attributes exposing the latest scheduling decision, blocker reason, next eligible probe time, effective mode, and relearn status.

### Changed
- Passive drift learning defaults are more useful after reset: minimum drift window is now 10 minutes and confidence threshold is now 0.2.
- Empty probe-history cold starts now prioritize the first valid probe instead of waiting for perfect diversity/opportunity.
- Thermal persistence keeps probe source metadata (`active`, `passive`, `history_backfill`) for clearer diagnostics.
- `analyze_drift_data` now has a NumPy-only fallback so passive/history learning still works when SciPy is unavailable.

### Verification
- `python -m py_compile custom_components/smart_climate/probe_scheduler.py custom_components/smart_climate/thermal_model.py custom_components/smart_climate/thermal_models.py custom_components/smart_climate/thermal_utils.py custom_components/smart_climate/thermal_manager.py custom_components/smart_climate/thermal_history_backfill.py custom_components/smart_climate/sensor_thermal.py custom_components/smart_climate/sensor.py custom_components/smart_climate/__init__.py`
- `python -m pytest tests/test_fast_relearn_thermal_learning.py tests/test_thermal_utils.py tests/test_probe_scheduler_edge_cases.py::TestProbeSchedulerEdgeCases::test_empty_probe_history_scenarios -q`
- Full `python -m pytest -q` is still blocked at collection by existing local HA test-harness/legacy issues unrelated to this change: missing mocked HA button/switch/weather/setup packages, missing optional `freezegun`/`pytest_homeassistant_custom_component`, stale removed config constants/imports, non-subscriptable mocked `DataUpdateCoordinator`, and an invalid legacy U+200C character in `tests/test_climate_thermal_priority.py`.

## v1.7.2 (2026-05-25)

### Summary
Smart Climate Control v1.7.2 is a pre-release hotfix for thermal model persistence after integration reloads or wrapped climate entity recreation. It keeps existing hysteresis/learning data intact and prevents empty default thermal snapshots from replacing learned thermal probe history.

### Fixed
- Preserve existing learned `thermal_data` when a transient reload produces an empty/default thermal snapshot with default tau values and `confidence: 0.0`.
- Recover restorable thermal data from the persistence backup during startup if the primary JSON was already overwritten with an empty/default thermal snapshot.

### Verification
- `python -m pytest tests/test_data_store_atomic_writes.py::TestThermalDataPreservation -q`
- `python -m py_compile custom_components/smart_climate/data_store.py`

## v1.7.1 (2026-05-25)

### Summary
Smart Climate Control v1.7.1 is a pre-release focused on closing the remaining open bug issues around configuration validation and centralized defaults. It keeps existing thermal timing behavior intact while making the source of truth explicit in `const.py`.

### Fixed
- Forecast configuration now rejects impossible heat-wave and clear-sky windows where `lookahead_hours < pre_action_hours + min_duration_hours`.
- `CycleMonitor` default minimum off/on durations now use `MIN_OFF_TIME_SECONDS` and `MIN_ON_TIME_SECONDS`.
- Thermal model and manager defaults now use shared priming/recovery constants instead of duplicating raw seconds.
- Mode behavior defaults now use shared away/sleep/boost constants.

### Issues
- Fixes #57
- Fixes #58
- Fixes #59
- Fixes #69

### Verification
- `for f in custom_components/smart_climate/manifest.json hacs.json custom_components/smart_climate/strings.json custom_components/smart_climate/translations/en.json; do python -m json.tool "$f" >/dev/null; done`
- `python -m py_compile custom_components/smart_climate/config_flow.py custom_components/smart_climate/cycle_monitor.py custom_components/smart_climate/mode_behaviors.py custom_components/smart_climate/thermal_models.py custom_components/smart_climate/thermal_manager.py custom_components/smart_climate/__init__.py`
- `python -m pytest tests/test_open_bug_issue_regressions.py tests/test_no_runtime_magic_defaults.py tests/test_config_flow_power_options.py tests/test_thermal_models.py tests/test_thermal_manager.py -q`

## v1.6.0 (2026-05-25)

### Summary
Smart Climate Control v1.6.0 is the production release for the 1.5.5 beta stabilization line. It turns the recent beta fixes into a stable HACS release focused on reliable diagnostics, safer Quiet Mode learning, cleaner dashboards, and removal of fragile runtime defaults.

### Added
- Production-ready Quiet Mode hysteresis learning with bounded probe behavior.
- Core-card Lovelace dashboard generation based on live Home Assistant entity registry data.
- More explicit diagnostic states and detail/source attributes for learning, Quiet Mode, compressor, and thermal telemetry.
- Transition-based power-correlation telemetry from observed compressor start/stop events.
- Regression coverage for runtime fallback constants and unsafe magic defaults.

### Fixed
- Hydrates humidity and derived diagnostic sensors during setup/reload so they no longer sit at `unknown` until a later poll.
- Prevents Quiet Mode from deadlocking hysteresis learning while still blocking probes during active compressor operation.
- Stores deliberate probe transitions as bounds/constraints instead of corrupting natural hysteresis samples.
- Generates dashboards without guessed helper IDs, custom-card dependencies, or placeholder entity IDs.
- Centers operating-window helper sensors on the live Smart Climate target instead of stale `24.0°C` defaults.
- Centralizes runtime fallback values for target temperature, outdoor/current temperature, comfort window, HVAC mode, weather entity ID, and Quiet Mode defaults.

### Upgrade notes
- No breaking changes.
- Existing configuration and learning data are preserved.
- A reset is not required for normal upgrades.
- If you used a generated dashboard from older beta releases, regenerate it after upgrading to get the cleaned core-card version.

### Verification
- `python -m json.tool custom_components/smart_climate/manifest.json`
- `python -m py_compile custom_components/smart_climate/const.py custom_components/smart_climate/climate.py custom_components/smart_climate/thermal_sensor.py custom_components/smart_climate/thermal_manager.py custom_components/smart_climate/coordinator.py custom_components/smart_climate/quiet_mode_controller.py custom_components/smart_climate/compressor_state_analyzer.py custom_components/smart_climate/mode_manager.py custom_components/smart_climate/__init__.py custom_components/smart_climate/config_flow.py custom_components/smart_climate/migration.py`
- `pytest tests/test_no_runtime_magic_defaults.py tests/test_quiet_mode_controller.py tests/test_quiet_mode_coordinator_data.py tests/test_thermal_sensor.py tests/test_thermal_manager.py tests/test_target_temperature.py -q`
- `pytest tests/test_config_flow_power_options.py -q`
- Full `pytest -q` is still blocked by existing collection/harness issues unrelated to this release prep: missing HA component mocks/packages, stale legacy imports, stale removed config constants, missing optional `freezegun`/`pytest_homeassistant_custom_component`, and invalid legacy test character in `tests/test_climate_thermal_priority.py`.

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
