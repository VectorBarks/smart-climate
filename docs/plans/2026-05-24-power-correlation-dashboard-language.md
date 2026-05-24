# Power Correlation + Dashboard Language Implementation Plan

> **For Hermes:** Implement directly with focused TDD; no Home Assistant runtime service calls are required.

**Goal:** Replace the placeholder power-correlation path with telemetry-derived accuracy and make dashboard language distinguish exact offsets, probe bounds, and insufficient data.

**Architecture:** Power correlation should be derived from persisted hysteresis transition events (`power_before`/`power_after`) instead of an empty placeholder history. Dashboard cards should consume climate attributes and explain learning state without implying that `0.0%` is necessarily failure.

**Tech Stack:** Home Assistant custom integration, Python unit tests, Lovelace YAML/markdown templates.

---

### Task 1: Preserve the dashboard-language regression

**Objective:** Add a runtime dashboard regression test that requires explicit labels for exact samples, probe constraints, sample progress, and power-correlation status.

**Files:**
- Modify: `tests/test_runtime_dashboard_generator.py`
- Modify later: `custom_components/smart_climate/dashboard/generator.py`

**Steps:**
1. Add a test generating `DashboardGenerator().generate_runtime_dashboard(...)`.
2. Assert the markdown contains:
   - `Exact compressor offsets`
   - `Probe-derived bounds`
   - `Sample progress`
   - `Power correlation`
   - `power_correlation_status_detail`
3. Run `pytest tests/test_runtime_dashboard_generator.py -q`; expected first run: fail before implementation.

### Task 2: Preserve telemetry-derived power-correlation behavior

**Objective:** Add failing tests proving `_get_power_prediction_history()` reads hysteresis transition events and `_calculate_power_correlation_accuracy()` uses configured/engine power-state thresholds.

**Files:**
- Modify: `tests/test_ac_learning_enhancement.py`
- Modify later: `custom_components/smart_climate/climate.py`

**Steps:**
1. Add transition-event fixture data with start/stop events and power before/after.
2. Assert `_get_power_prediction_history()` emits before/after checks with expected `predicted_state` values.
3. Assert calculated accuracy counts active-vs-idle checks from transition telemetry.
4. Assert `extra_state_attributes` exposes `power_correlation_sample_count`, `power_correlation_status_detail`, and `power_correlation_source`.
5. Run focused tests; expected first run: fail on placeholder `[]` and missing attributes.

### Task 3: Implement source telemetry and status details

**Objective:** Replace the empty placeholder history while preserving safe `0.0` behavior for missing/insufficient data.

**Files:**
- Modify: `custom_components/smart_climate/climate.py`

**Implementation:**
1. Add helpers to classify actual power via `self._offset_engine._get_power_state()` when available.
2. Build prediction-history entries from `hysteresis_learner.get_transition_events()`:
   - start: before expected `idle`, after expected `active`
   - stop: before expected `active`, after expected `idle`
3. Treat `active` as any non-idle power state (`low`, `moderate`, `high`).
4. Keep `<5` checks as insufficient and return `0.0`, but expose sample count/status so dashboards do not call it failure.

### Task 4: Improve dashboard language

**Objective:** Make generated dashboards explain what the learning telemetry means.

**Files:**
- Modify: `custom_components/smart_climate/dashboard/generator.py`
- Modify: `custom_components/smart_climate/dashboard/dashboard_generic.yaml`

**Implementation:**
1. Replace ambiguous `Compressor offsets` / `Probe bounds` wording with explicit sections:
   - exact compressor offsets
   - probe-derived bounds
   - sample progress
   - power correlation status
2. In generic YAML, show `collecting data` when correlation sample count is below 5 instead of painting `0.0%` red.
3. Keep cards core-safe in runtime generator.

### Task 5: Verify

**Commands:**
```bash
pytest tests/test_runtime_dashboard_generator.py tests/test_ac_learning_enhancement.py -q
python -m py_compile custom_components/smart_climate/climate.py custom_components/smart_climate/dashboard/generator.py
```

**Success Criteria:**
- Focused tests pass.
- Changed Python files compile.
- `git diff` shows only the planned test, source, dashboard, and plan changes.
