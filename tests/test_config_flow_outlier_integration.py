"""ABOUTME: Comprehensive config flow outlier detection integration tests.
Tests complete user interaction flow with outlier detection configuration."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys

# Mock homeassistant modules
sys.modules['homeassistant.helpers.selector'] = MagicMock()
sys.modules['homeassistant.helpers.entity_registry'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()

# Mock config_entries and data_entry_flow
mock_config_entries = MagicMock()
mock_config_entries.ConfigFlow = MagicMock()
mock_config_entries.OptionsFlow = MagicMock()
mock_config_entries.ConfigEntry = MagicMock()
sys.modules['homeassistant.config_entries'] = mock_config_entries

# Mock data_entry_flow
mock_data_entry_flow = MagicMock()
mock_data_entry_flow.FlowResultType = MagicMock()
mock_data_entry_flow.FlowResultType.FORM = "form"
mock_data_entry_flow.FlowResultType.CREATE_ENTRY = "create_entry"
mock_data_entry_flow.FlowResult = dict
sys.modules['homeassistant.data_entry_flow'] = mock_data_entry_flow

from custom_components.smart_climate.const import (
    DOMAIN,
    CONF_CLIMATE_ENTITY,
    CONF_ROOM_SENSOR,
    CONF_OUTLIER_DETECTION_ENABLED,
    CONF_OUTLIER_SENSITIVITY,
    DEFAULT_OUTLIER_DETECTION_ENABLED,
    DEFAULT_OUTLIER_SENSITIVITY,
)


@pytest.fixture
def hass():
    """Create a mock Home Assistant instance."""
    mock_hass = MagicMock()
    mock_hass.states = MagicMock()
    mock_hass.states.async_all = MagicMock(return_value=[])
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[])
    mock_hass.data = {DOMAIN: {}}
    return mock_hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    config_entry.data = {
        CONF_CLIMATE_ENTITY: "climate.test",
        CONF_ROOM_SENSOR: "sensor.test_temp",
    }
    config_entry.options = {}
    return config_entry


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.outlier_detection_enabled = True
    coordinator.data = MagicMock()
    coordinator.data.outliers = {}
    coordinator.data.outlier_count = 0
    coordinator.data.outlier_statistics = {
        "enabled": True,
        "temperature_outliers": 0,
        "power_outliers": 0,
        "total_samples": 10,
        "outlier_rate": 0.0
    }
    return coordinator


@pytest.fixture  
def mock_outlier_detector():
    """Create a mock outlier detector."""
    detector = MagicMock()
    detector.is_temperature_outlier.return_value = False
    detector.is_power_outlier.return_value = False
    detector.get_history_size.return_value = 10
    detector.has_sufficient_data.return_value = True
    return detector


class TestConfigFlowOutlierIntegration:
    """Test complete config flow outlier detection integration."""

    @pytest.mark.asyncio
    async def test_initial_setup_includes_outlier_defaults(self, hass, mock_config_entry):
        """Test initial setup includes outlier detection defaults."""
        from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass
        options_flow.config_entry = mock_config_entry
        
        # Mock empty initial options
        mock_config_entry.options = {}
        mock_config_entry.data = {
            CONF_CLIMATE_ENTITY: "climate.test",
            CONF_ROOM_SENSOR: "sensor.test_temp",
        }
        
        result = await options_flow.async_step_init()
        
        # Verify form is created
        assert result["type"] == "form"
        assert result["step_id"] == "init"
        
        # Check schema includes outlier detection with defaults
        schema = result["data_schema"].schema
        
        # Find outlier detection fields
        outlier_enabled_field = None
        outlier_sensitivity_field = None
        
        for key, selector in schema.items():
            key_str = str(key)
            if CONF_OUTLIER_DETECTION_ENABLED in key_str:
                outlier_enabled_field = key
            elif CONF_OUTLIER_SENSITIVITY in key_str:
                outlier_sensitivity_field = key
        
        # Verify fields exist with correct defaults
        assert outlier_enabled_field is not None
        assert outlier_sensitivity_field is not None
        assert outlier_enabled_field.default == DEFAULT_OUTLIER_DETECTION_ENABLED
        assert outlier_sensitivity_field.default == DEFAULT_OUTLIER_SENSITIVITY
        
    @pytest.mark.asyncio
    async def test_options_flow_user_interaction(self, hass, mock_config_entry):
        """Test user can modify outlier detection settings through options flow."""
        from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass  
        options_flow.config_entry = mock_config_entry
        
        # User input with outlier detection changes
        user_input = {
            CONF_OUTLIER_DETECTION_ENABLED: False,
            CONF_OUTLIER_SENSITIVITY: 3.5,
            "max_offset": 4.0,  # Include other configuration
        }
        
        result = await options_flow.async_step_init(user_input)
        
        # Verify entry is created with user choices
        assert result["type"] == "create_entry"
        assert result["data"][CONF_OUTLIER_DETECTION_ENABLED] is False
        assert result["data"][CONF_OUTLIER_SENSITIVITY] == 3.5
        assert result["data"]["max_offset"] == 4.0

    @pytest.mark.asyncio
    async def test_configuration_validation_edge_cases(self, hass, mock_config_entry):
        """Test validation with edge cases (min/max sensitivity values)."""
        from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass
        options_flow.config_entry = mock_config_entry
        
        # Test minimum sensitivity value
        user_input_min = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 1.0,  # Minimum allowed
        }
        
        result_min = await options_flow.async_step_init(user_input_min)
        assert result_min["type"] == "create_entry"
        assert result_min["data"][CONF_OUTLIER_SENSITIVITY] == 1.0
        
        # Test maximum sensitivity value  
        user_input_max = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 5.0,  # Maximum allowed
        }
        
        result_max = await options_flow.async_step_init(user_input_max)
        assert result_max["type"] == "create_entry"
        assert result_max["data"][CONF_OUTLIER_SENSITIVITY] == 5.0

    @pytest.mark.asyncio  
    async def test_config_changes_propagate_to_coordinator(self, hass, mock_config_entry, mock_outlier_detector):
        """Test config changes reach coordinator during initialization."""
        from custom_components.smart_climate.coordinator import SmartClimateCoordinator
        from custom_components.smart_climate.sensor_manager import SensorManager
        from custom_components.smart_climate.offset_engine import OffsetEngine
        from custom_components.smart_climate.mode_manager import ModeManager
        
        # Mock dependencies
        mock_sensor_manager = MagicMock(spec=SensorManager)
        mock_offset_engine = MagicMock(spec=OffsetEngine)
        mock_mode_manager = MagicMock(spec=ModeManager)
        
        # Config with outlier detection enabled
        outlier_config = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 3.0,
        }
        
        # Test coordinator initialization with outlier config
        with patch('custom_components.smart_climate.coordinator.OutlierDetector') as mock_detector_class:
            mock_detector_class.return_value = mock_outlier_detector
            
            coordinator = SmartClimateCoordinator(
                hass=hass,
                update_interval=180,
                sensor_manager=mock_sensor_manager,
                offset_engine=mock_offset_engine,
                mode_manager=mock_mode_manager,
                outlier_detection_config=outlier_config
            )
            
            # Verify outlier detection is enabled
            assert coordinator.outlier_detection_enabled is True
            assert coordinator._outlier_detector is not None
            
            # Verify OutlierDetector was initialized with config
            mock_detector_class.assert_called_once_with(config=outlier_config)

    @pytest.mark.asyncio
    async def test_disable_outlier_detection_removes_sensors(self, hass, mock_config_entry):
        """Test disabling outlier detection affects sensor creation."""
        from custom_components.smart_climate.coordinator import SmartClimateCoordinator
        from custom_components.smart_climate.sensor_manager import SensorManager
        from custom_components.smart_climate.offset_engine import OffsetEngine
        from custom_components.smart_climate.mode_manager import ModeManager
        
        # Mock dependencies
        mock_sensor_manager = MagicMock(spec=SensorManager)
        mock_offset_engine = MagicMock(spec=OffsetEngine)
        mock_mode_manager = MagicMock(spec=ModeManager)
        
        # Config with outlier detection disabled
        outlier_config = None  # Disabled
        
        coordinator = SmartClimateCoordinator(
            hass=hass,
            update_interval=180,
            sensor_manager=mock_sensor_manager,
            offset_engine=mock_offset_engine,
            mode_manager=mock_mode_manager,
            outlier_detection_config=outlier_config
        )
        
        # Verify outlier detection is disabled
        assert coordinator.outlier_detection_enabled is False
        assert coordinator._outlier_detector is None
        
        # Execute update and verify no outlier data is generated
        mock_sensor_manager.get_room_temperature.return_value = 22.0
        mock_sensor_manager.get_outdoor_temperature.return_value = 30.0
        mock_sensor_manager.get_power_consumption.return_value = 150.0
        
        mock_mode_manager.get_adjustments.return_value = MagicMock()
        mock_mode_manager.current_mode = "none"
        
        mock_offset_engine.calculate_offset.return_value = MagicMock(offset=2.5)
        
        data = await coordinator._async_update_data()
        
        # Verify outlier fields are empty/disabled
        assert data.outliers == {}
        assert data.outlier_count == 0
        assert data.outlier_statistics["enabled"] is False

    @pytest.mark.asyncio
    async def test_enable_outlier_detection_creates_sensors(self, hass, mock_config_entry, mock_outlier_detector):
        """Test enabling outlier detection creates sensor data."""
        from custom_components.smart_climate.coordinator import SmartClimateCoordinator
        from custom_components.smart_climate.sensor_manager import SensorManager
        from custom_components.smart_climate.offset_engine import OffsetEngine
        from custom_components.smart_climate.mode_manager import ModeManager
        
        # Mock dependencies
        mock_sensor_manager = MagicMock(spec=SensorManager)
        mock_offset_engine = MagicMock(spec=OffsetEngine)
        mock_mode_manager = MagicMock(spec=ModeManager)
        
        # Config with outlier detection enabled
        outlier_config = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.5,
        }
        
        with patch('custom_components.smart_climate.coordinator.OutlierDetector') as mock_detector_class:
            # Configure outlier detector behavior
            mock_outlier_detector.is_temperature_outlier.return_value = True  # Temperature is outlier
            mock_outlier_detector.is_power_outlier.return_value = False  # Power is not outlier
            mock_outlier_detector.get_history_size.return_value = 25
            mock_outlier_detector.has_sufficient_data.return_value = True
            mock_detector_class.return_value = mock_outlier_detector
            
            coordinator = SmartClimateCoordinator(
                hass=hass,
                update_interval=180,
                sensor_manager=mock_sensor_manager,
                offset_engine=mock_offset_engine,
                mode_manager=mock_mode_manager,
                outlier_detection_config=outlier_config
            )
            
            # Setup sensor data
            mock_sensor_manager.get_room_temperature.return_value = 22.0
            mock_sensor_manager.get_outdoor_temperature.return_value = 30.0
            mock_sensor_manager.get_power_consumption.return_value = 150.0
            
            mock_mode_manager.get_adjustments.return_value = MagicMock()
            mock_mode_manager.current_mode = "none"
            
            mock_offset_engine.calculate_offset.return_value = MagicMock(offset=2.5)
            
            # Execute update
            data = await coordinator._async_update_data()
            
            # Verify outlier detection is active and data is populated
            assert data.outlier_statistics["enabled"] is True
            assert data.outliers["temperature"] is True  # Temperature outlier detected
            assert data.outliers["power"] is False  # Power not outlier
            assert data.outlier_count == 1  # One outlier total
            assert data.outlier_statistics["temperature_outliers"] == 1
            assert data.outlier_statistics["power_outliers"] == 0
            assert data.outlier_statistics["total_samples"] == 2
            assert data.outlier_statistics["outlier_rate"] == 0.5
            
            # Verify detector methods were called
            mock_outlier_detector.is_temperature_outlier.assert_called_once_with(22.0)
            mock_outlier_detector.is_power_outlier.assert_called_once_with(150.0)
            mock_outlier_detector.add_temperature_sample.assert_called_once_with(22.0)
            mock_outlier_detector.add_power_sample.assert_called_once_with(150.0)

    @pytest.mark.asyncio
    async def test_sensitivity_changes_affect_detection(self, hass, mock_config_entry):
        """Test sensitivity changes affect outlier detection behavior."""
        from custom_components.smart_climate.coordinator import SmartClimateCoordinator
        from custom_components.smart_climate.sensor_manager import SensorManager
        from custom_components.smart_climate.offset_engine import OffsetEngine
        from custom_components.smart_climate.mode_manager import ModeManager
        
        # Mock dependencies
        mock_sensor_manager = MagicMock(spec=SensorManager)
        mock_offset_engine = MagicMock(spec=OffsetEngine)
        mock_mode_manager = MagicMock(spec=ModeManager)
        
        # Test with high sensitivity (more outliers detected)
        high_sensitivity_config = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 1.0,  # Very sensitive
        }
        
        with patch('custom_components.smart_climate.coordinator.OutlierDetector') as mock_detector_class:
            # Mock detector for high sensitivity
            mock_high_sensitivity_detector = MagicMock()
            mock_high_sensitivity_detector.is_temperature_outlier.return_value = True  # Detects outlier
            mock_high_sensitivity_detector.is_power_outlier.return_value = True  # Detects outlier
            mock_high_sensitivity_detector.get_history_size.return_value = 10
            mock_high_sensitivity_detector.has_sufficient_data.return_value = True
            mock_detector_class.return_value = mock_high_sensitivity_detector
            
            coordinator_high = SmartClimateCoordinator(
                hass=hass,
                update_interval=180,
                sensor_manager=mock_sensor_manager,
                offset_engine=mock_offset_engine,
                mode_manager=mock_mode_manager,
                outlier_detection_config=high_sensitivity_config
            )
            
            # Verify high sensitivity detector was created with correct config
            mock_detector_class.assert_called_with(config=high_sensitivity_config)
        
        # Test with low sensitivity (fewer outliers detected)
        low_sensitivity_config = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 5.0,  # Very insensitive
        }
        
        with patch('custom_components.smart_climate.coordinator.OutlierDetector') as mock_detector_class:
            # Mock detector for low sensitivity
            mock_low_sensitivity_detector = MagicMock()
            mock_low_sensitivity_detector.is_temperature_outlier.return_value = False  # No outlier
            mock_low_sensitivity_detector.is_power_outlier.return_value = False  # No outlier
            mock_low_sensitivity_detector.get_history_size.return_value = 10
            mock_low_sensitivity_detector.has_sufficient_data.return_value = True
            mock_detector_class.return_value = mock_low_sensitivity_detector
            
            coordinator_low = SmartClimateCoordinator(
                hass=hass,
                update_interval=180,
                sensor_manager=mock_sensor_manager,
                offset_engine=mock_offset_engine,
                mode_manager=mock_mode_manager,
                outlier_detection_config=low_sensitivity_config
            )
            
            # Verify low sensitivity detector was created with correct config
            mock_detector_class.assert_called_with(config=low_sensitivity_config)
        
        # Verify both coordinators have outlier detection enabled
        assert coordinator_high.outlier_detection_enabled is True
        assert coordinator_low.outlier_detection_enabled is True
        assert coordinator_high._outlier_detector is not None
        assert coordinator_low._outlier_detector is not None

    @pytest.mark.asyncio
    async def test_config_entry_reload_on_options_change(self, hass, mock_config_entry):
        """Test that changing outlier options triggers config entry reload."""
        from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass
        options_flow.config_entry = mock_config_entry
        
        # Setup initial options
        mock_config_entry.options = {
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.5,
        }
        
        # User changes outlier settings
        user_input = {
            CONF_OUTLIER_DETECTION_ENABLED: False,  # Disable outlier detection
            CONF_OUTLIER_SENSITIVITY: 4.0,  # Change sensitivity
        }
        
        # Mock the async_create_entry to verify reload trigger
        with patch.object(options_flow, 'async_create_entry') as mock_create:
            mock_create.return_value = {"type": "create_entry", "data": user_input}
            
            result = await options_flow.async_step_init(user_input)
            
            # Verify async_create_entry was called with correct data
            mock_create.assert_called_once_with(title="", data=user_input)
            
            # Verify result contains the new configuration
            assert result["type"] == "create_entry"
            assert result["data"][CONF_OUTLIER_DETECTION_ENABLED] is False
            assert result["data"][CONF_OUTLIER_SENSITIVITY] == 4.0

    @pytest.mark.asyncio
    async def test_options_preserve_non_outlier_settings(self, hass, mock_config_entry):
        """Test that outlier options changes preserve other existing settings."""
        from custom_components.smart_climate.config_flow import SmartClimateOptionsFlow
        
        options_flow = SmartClimateOptionsFlow()
        options_flow.hass = hass
        options_flow.config_entry = mock_config_entry
        
        # Setup existing options with various settings
        existing_options = {
            "max_offset": 3.5,
            "update_interval": 300,
            "ml_enabled": True,
            CONF_OUTLIER_DETECTION_ENABLED: True,
            CONF_OUTLIER_SENSITIVITY: 2.5,
        }
        mock_config_entry.options = existing_options
        
        # User only changes outlier settings
        user_input = {
            "max_offset": 3.5,  # Keep same
            "update_interval": 300,  # Keep same
            "ml_enabled": True,  # Keep same
            CONF_OUTLIER_DETECTION_ENABLED: False,  # Change this
            CONF_OUTLIER_SENSITIVITY: 3.0,  # Change this
        }
        
        result = await options_flow.async_step_init(user_input)
        
        # Verify all settings are preserved/updated correctly
        assert result["type"] == "create_entry"
        assert result["data"]["max_offset"] == 3.5  # Preserved
        assert result["data"]["update_interval"] == 300  # Preserved
        assert result["data"]["ml_enabled"] is True  # Preserved
        assert result["data"][CONF_OUTLIER_DETECTION_ENABLED] is False  # Changed
        assert result["data"][CONF_OUTLIER_SENSITIVITY] == 3.0  # Changed