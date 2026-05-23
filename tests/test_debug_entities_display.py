"""Regression tests for diagnostic/debug entity display states."""

from unittest.mock import Mock

from custom_components.smart_climate.cycle_monitor import CycleMonitor
from custom_components.smart_climate.sensor import (
    CompressorStateSensor,
    QuietModeStatusSensor,
    QuietModeSuppressionSensor,
    SeasonalAdaptationSensor,
    WeatherForecastSensor,
)
from custom_components.smart_climate.sensor_ac_learning import TemperatureWindowSensor
from custom_components.smart_climate.sensor_system_health import ConvergenceTrendSensor
from custom_components.smart_climate.sensor_thermal import (
    AverageOffCycleSensor,
    AverageOnCycleSensor,
    CycleHealthSensor,
    ProbingActiveSensor,
    ShadowModeSensor,
)
from custom_components.smart_climate.thermal_models import ThermalState


def _coordinator(data):
    coordinator = Mock()
    coordinator.data = data
    coordinator.last_update_success = True
    coordinator.async_add_listener = Mock(return_value=lambda: None)
    return coordinator


def _config_entry():
    entry = Mock()
    entry.entry_id = "entry-1"
    entry.unique_id = "uid-1"
    entry.title = "SCC Test"
    entry.options = {}
    return entry


def test_weather_forecast_sensor_has_text_state_in_sensor_platform():
    sensor = WeatherForecastSensor(
        _coordinator({"weather_forecast": True}),
        "climate.test",
        _config_entry(),
    )

    assert sensor.is_on is True
    assert sensor.native_value == "enabled"
    assert sensor.extra_state_attributes["status_detail"] == "Forecast engine is wired and active"


def test_seasonal_adaptation_sensor_has_text_state_and_context():
    sensor = SeasonalAdaptationSensor(
        _coordinator({
            "seasonal_data": {
                "enabled": True,
                "contribution": 12.5,
                "pattern_count": 3,
                "outdoor_temp_bucket": "25-30°C",
                "accuracy": 81.0,
            }
        }),
        "climate.test",
        _config_entry(),
    )

    assert sensor.is_on is True
    assert sensor.native_value == "enabled"
    assert sensor.extra_state_attributes["pattern_count"] == 3


def test_convergence_trend_accepts_learning_state_from_offset_engine():
    sensor = ConvergenceTrendSensor(
        _coordinator({"system_health": {"convergence_trend": "learning"}}),
        "climate.test",
        _config_entry(),
    )

    assert sensor.native_value == "learning"
    assert "Collecting enough samples" in sensor.extra_state_attributes["status_detail"]


def test_quiet_mode_sensors_explain_state_source():
    entry = _config_entry()
    data = {
        "quiet_mode_status": "enabled",
        "quiet_mode_suppressions": 4,
        "compressor_state": "idle",
    }

    status = QuietModeStatusSensor(_coordinator(data), "climate.test", entry)
    suppressions = QuietModeSuppressionSensor(_coordinator(data), "climate.test", entry)
    compressor = CompressorStateSensor(_coordinator(data), "climate.test", entry)

    assert status.extra_state_attributes["source"] == "dashboard_coordinator.quiet_mode_status"
    assert suppressions.extra_state_attributes["status_detail"] == "Quiet Mode has suppressed 4 non-useful adjustment beep(s)"
    assert compressor.extra_state_attributes["status_detail"] == "Compressor is idle according to the configured power sensor"


def test_temperature_window_reports_learning_instead_of_unknown_with_context():
    sensor = TemperatureWindowSensor(
        _coordinator({
            "ac_behavior": {"temperature_window": None, "hysteresis_cycle_count": 0},
            "learning_info": {
                "hysteresis_enabled": True,
                "hysteresis_ready": False,
                "hysteresis_state": "learning_hysteresis",
                "start_samples_collected": 1,
                "stop_samples_collected": 0,
            },
        }),
        "climate.test",
        _config_entry(),
    )

    assert sensor.native_value == "learning"
    attrs = sensor.extra_state_attributes
    assert attrs["hysteresis_enabled"] is True
    assert "Collecting compressor" in attrs["status_detail"]


def test_thermal_binary_like_sensors_expose_sensor_states():
    entry = _config_entry()
    coordinator = _coordinator({})
    thermal_manager = Mock()
    thermal_manager.current_state = ThermalState.PRIMING
    thermal_components = {
        "shadow_mode": False,
        "thermal_manager": thermal_manager,
        "cycle_monitor": CycleMonitor(),
    }

    shadow = ShadowModeSensor(coordinator, "climate.test", entry)
    shadow._get_thermal_components = lambda: thermal_components
    probing = ProbingActiveSensor(coordinator, "climate.test", entry)
    probing._get_thermal_components = lambda: thermal_components
    cycle_health = CycleHealthSensor(coordinator, "climate.test", entry)
    cycle_health._get_thermal_components = lambda: thermal_components

    assert shadow.native_value == "disabled"
    assert probing.native_value == "inactive"
    assert cycle_health.native_value == "ok"


def test_average_cycle_sensors_use_cycle_monitor_tuple_api():
    entry = _config_entry()
    coordinator = _coordinator({})
    cycle_monitor = CycleMonitor()
    cycle_monitor.record_cycle(480, True)
    cycle_monitor.record_cycle(720, False)
    thermal_components = {"cycle_monitor": cycle_monitor}

    avg_on = AverageOnCycleSensor(coordinator, "climate.test", entry)
    avg_on._get_thermal_components = lambda: thermal_components
    avg_off = AverageOffCycleSensor(coordinator, "climate.test", entry)
    avg_off._get_thermal_components = lambda: thermal_components

    assert avg_on.native_value == 480.0
    assert avg_off.native_value == 720.0
    assert avg_on.extra_state_attributes["recorded_cycles"] == 2
