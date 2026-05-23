# Release Notes

## v1.5.5-beta10 (2026-05-23)

### Summary
Quiet Mode dashboard sensors now receive live coordinator data instead of reading fields that were never populated.

### Fixed
- `sensor.*_compressor_state` now reports `idle` or `active` from the configured AC power sensor and idle threshold.
- `sensor.*_quiet_mode_status` now reports enabled/disabled coordinator state.
- `sensor.*_quiet_mode_suppressions` now mirrors the live Quiet Mode controller suppression count.

### Validation
- Added a focused regression test for real `SmartClimateData` Quiet Mode fields and coordinator population.
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
