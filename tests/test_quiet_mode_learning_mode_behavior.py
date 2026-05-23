"""Regression tests for quiet-mode hysteresis learning probes."""

import logging
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.components.climate.const import HVACMode

from custom_components.smart_climate.climate import SmartClimateEntity
from custom_components.smart_climate.models import ModeAdjustments, OffsetResult
from custom_components.smart_climate.offset_engine import HysteresisLearner
from custom_components.smart_climate.quiet_mode_controller import QuietModeController
from custom_components.smart_climate.compressor_state_analyzer import CompressorStateAnalyzer
from tests.fixtures.mock_entities import (
    create_mock_coordinator,
    create_mock_hass,
    create_mock_mode_manager,
    create_mock_sensor_manager,
    create_mock_state,
    create_mock_temperature_controller,
)


def _known_hysteresis_learner() -> HysteresisLearner:
    learner = HysteresisLearner(min_samples=2)
    for temp in (23.8, 24.0):
        learner.record_transition("start", temp)
    for temp in (23.0, 23.2):
        learner.record_transition("stop", temp)
    return learner


def test_unknown_thresholds_allow_learning_probe_instead_of_suppressing():
    controller = QuietModeController(
        enabled=True,
        analyzer=CompressorStateAnalyzer(power_threshold=50.0),
        logger=logging.getLogger(__name__),
    )
    learner = HysteresisLearner()

    progressive = controller.get_progressive_adjustment(
        current_room_temp=23.9,
        current_setpoint=28.0,
        hysteresis_learner=learner,
        hvac_mode="cool",
        target_setpoint=23.2,
    )

    assert progressive == pytest.approx(27.5)

    should_suppress, reason = controller.should_suppress_adjustment(
        current_room_temp=23.9,
        current_setpoint=28.0,
        new_setpoint=progressive,
        power=15.0,
        hvac_mode="cool",
        hysteresis_learner=learner,
    )

    assert should_suppress is False
    assert reason == "learning mode: probing compressor start threshold"


def test_known_thresholds_disable_learning_probe_and_keep_quiet_suppression():
    controller = QuietModeController(
        enabled=True,
        analyzer=CompressorStateAnalyzer(power_threshold=50.0),
        logger=logging.getLogger(__name__),
    )
    learner = _known_hysteresis_learner()

    progressive = controller.get_progressive_adjustment(
        current_room_temp=23.9,
        current_setpoint=24.0,
        hysteresis_learner=learner,
        hvac_mode="cool",
        target_setpoint=23.8,
    )

    assert progressive is None

    should_suppress, reason = controller.should_suppress_adjustment(
        current_room_temp=23.9,
        current_setpoint=24.0,
        new_setpoint=23.95,
        power=15.0,
        hvac_mode="cool",
        hysteresis_learner=learner,
    )

    assert should_suppress is True
    assert "won't activate" in reason


@pytest.mark.asyncio
async def test_smart_climate_sends_progressive_probe_when_quiet_mode_must_learn():
    hass = create_mock_hass()
    hass.data = {}
    hass.states.set(
        "climate.argo",
        create_mock_state(
            HVACMode.COOL,
            {
                "temperature": 28.0,
                "current_temperature": 28.0,
                "hvac_modes": [HVACMode.OFF, HVACMode.COOL],
            },
            entity_id="climate.argo",
        ),
    )

    offset_engine = Mock()
    offset_engine._hysteresis_learner = HysteresisLearner()
    offset_engine.calculate_offset.return_value = OffsetResult(
        offset=0.0,
        clamped=False,
        reason="test",
        confidence=1.0,
    )
    offset_engine._enable_learning = False

    sensor_manager = create_mock_sensor_manager()
    sensor_manager.get_room_temperature.return_value = 23.9
    sensor_manager.get_outdoor_temperature.return_value = None
    sensor_manager.get_power_consumption.return_value = 15.0

    mode_manager = create_mock_mode_manager()
    mode_manager.current_mode = "none"
    mode_manager.get_adjustments.return_value = ModeAdjustments(
        temperature_override=None,
        offset_adjustment=0.0,
        update_interval_override=None,
        boost_offset=0.0,
    )

    temperature_controller = create_mock_temperature_controller()
    temperature_controller.apply_offset_and_limits.return_value = 23.2
    temperature_controller.send_temperature_command = AsyncMock()

    entity = SmartClimateEntity(
        hass=hass,
        config={"name": "Smart Argo", "power_sensor": "sensor.argo_power"},
        wrapped_entity_id="climate.argo",
        room_sensor_id="sensor.room_temp",
        offset_engine=offset_engine,
        sensor_manager=sensor_manager,
        mode_manager=mode_manager,
        temperature_controller=temperature_controller,
        coordinator=create_mock_coordinator(),
    )

    await entity._apply_temperature_with_offset(23.5)

    temperature_controller.send_temperature_command.assert_awaited_once_with(
        "climate.argo",
        27.5,
    )
