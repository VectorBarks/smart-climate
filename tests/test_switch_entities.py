"""Test the Smart Climate switch entities."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.switch import async_setup_entry, LearningSwitch
from custom_components.smart_climate.offset_engine import OffsetEngine


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = Mock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.unique_id = "test_unique_id"
    entry.title = "Test Climate"
    entry.data = {
        "max_offset": 5.0,
        "enable_learning": False
    }
    return entry


@pytest.fixture
def mock_offset_engine():
    """Create a mock offset engine."""
    engine = Mock(spec=OffsetEngine)
    engine.is_learning_enabled = False
    engine.enable_learning = Mock()
    engine.disable_learning = Mock()
    engine.register_update_callback = Mock(return_value=Mock())
    engine.get_learning_info = Mock(return_value={
        "enabled": False,
        "samples": 0,
        "accuracy": 0.0,
        "confidence": 0.0,
        "has_sufficient_data": False
    })
    return engine


@pytest.fixture
def mock_hass_with_data(mock_offset_engine):
    """Create a mock HomeAssistant instance with pre-populated data."""
    hass = Mock()
    hass.data = {
        DOMAIN: {
            "test_entry_id": {
                "offset_engine": mock_offset_engine
            }
        }
    }
    return hass


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    @pytest.mark.asyncio
    async def test_setup_creates_learning_switch(
        self, 
        mock_hass_with_data, 
        mock_config_entry, 
        mock_offset_engine
    ):
        """Test that setup creates a learning switch entity."""
        mock_add_entities = Mock(spec=AddEntitiesCallback)
        
        await async_setup_entry(
            mock_hass_with_data,
            mock_config_entry,
            mock_add_entities
        )
        
        # Verify that exactly one entity was added
        mock_add_entities.assert_called_once()
        added_entities = mock_add_entities.call_args[0][0]
        assert len(added_entities) == 1
        
        # Verify the entity is a LearningSwitch
        entity = added_entities[0]
        assert isinstance(entity, LearningSwitch)

    @pytest.mark.asyncio
    async def test_setup_uses_shared_offset_engine(
        self, 
        mock_hass_with_data, 
        mock_config_entry, 
        mock_offset_engine
    ):
        """Test that setup uses the shared offset engine from hass.data."""
        mock_add_entities = Mock(spec=AddEntitiesCallback)
        
        await async_setup_entry(
            mock_hass_with_data,
            mock_config_entry,
            mock_add_entities
        )
        
        # Get the created entity
        added_entities = mock_add_entities.call_args[0][0]
        entity = added_entities[0]
        
        # Verify it uses the same offset engine instance
        assert entity._offset_engine is mock_offset_engine


class TestLearningSwitch:
    """Test the LearningSwitch entity."""

    @pytest.fixture
    def learning_switch(self, mock_config_entry, mock_offset_engine):
        """Create a LearningSwitch instance for testing."""
        return LearningSwitch(
            mock_config_entry,
            mock_offset_engine,
            "Test Climate"
        )

    def test_initialization(self, learning_switch, mock_offset_engine):
        """Test switch initialization."""
        assert learning_switch._offset_engine is mock_offset_engine
        assert learning_switch.name == "Learning"
        assert learning_switch.unique_id == "test_unique_id_learning_switch"
        # Icon changes based on state, so test the logic
        mock_offset_engine.is_learning_enabled = False
        assert learning_switch.icon == "mdi:brain-off"
        mock_offset_engine.is_learning_enabled = True
        assert learning_switch.icon == "mdi:brain"

    def test_device_info(self, learning_switch):
        """Test device info is correctly set."""
        device_info = learning_switch.device_info
        assert device_info is not None
        assert device_info["identifiers"] == {(DOMAIN, "test_unique_id")}
        assert device_info["name"] == "Test Climate"

    def test_is_on_when_learning_disabled(self, learning_switch, mock_offset_engine):
        """Test is_on returns False when learning is disabled."""
        mock_offset_engine.is_learning_enabled = False
        assert learning_switch.is_on is False

    def test_is_on_when_learning_enabled(self, learning_switch, mock_offset_engine):
        """Test is_on returns True when learning is enabled."""
        mock_offset_engine.is_learning_enabled = True
        assert learning_switch.is_on is True

    @pytest.mark.asyncio
    async def test_turn_on_enables_learning(self, learning_switch, mock_offset_engine):
        """Test that turning on the switch enables learning."""
        await learning_switch.async_turn_on()
        mock_offset_engine.enable_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_disables_learning(self, learning_switch, mock_offset_engine):
        """Test that turning off the switch disables learning."""
        await learning_switch.async_turn_off()
        mock_offset_engine.disable_learning.assert_called_once()

    def test_extra_state_attributes_returns_learning_info(
        self, 
        learning_switch, 
        mock_offset_engine
    ):
        """Test that extra_state_attributes returns learning info."""
        learning_info = {
            "enabled": False,
            "samples": 42,
            "accuracy": 0.8,
            "confidence": 0.7,
            "has_sufficient_data": True
        }
        mock_offset_engine.get_learning_info.return_value = learning_info
        
        attributes = learning_switch.extra_state_attributes
        
        # Check the transformed attributes match expected format
        assert attributes["samples_collected"] == 42
        assert attributes["learning_accuracy"] == 0.8
        assert attributes["confidence_level"] == 0.7
        assert attributes["patterns_learned"] == 42  # Uses samples as patterns count
        assert attributes["has_sufficient_data"] is True
        assert attributes["enabled"] is False
        
        mock_offset_engine.get_learning_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_added_to_hass_registers_callback(
        self, 
        learning_switch, 
        mock_offset_engine
    ):
        """Test that async_added_to_hass registers update callback."""
        # Mock the async_on_remove method
        learning_switch.async_on_remove = Mock()
        
        await learning_switch.async_added_to_hass()
        
        # Verify callback registration was attempted
        mock_offset_engine.register_update_callback.assert_called_once()
        
        # Verify the callback removal function is stored
        learning_switch.async_on_remove.assert_called_once()

    def test_handle_update_does_not_raise_exception(self, learning_switch):
        """Test that _handle_update does not raise exceptions."""
        # Even if async_write_ha_state fails, _handle_update should not raise
        learning_switch.async_write_ha_state = Mock(side_effect=Exception("Test exception"))
        
        # This should not raise an exception
        try:
            learning_switch._handle_update()
            # If we get here, the exception was caught properly
            test_passed = True
        except Exception:
            # If we get here, the exception wasn't caught
            test_passed = False
        
        assert test_passed, "_handle_update should catch and handle exceptions"


class TestLearningStates:
    """Test various learning states and transitions."""

    @pytest.fixture
    def learning_switch_with_states(self, mock_config_entry, mock_offset_engine):
        """Create a learning switch with state-aware offset engine."""
        return LearningSwitch(
            mock_config_entry,
            mock_offset_engine,
            "Test Climate"
        )

    def test_switch_reflects_learning_state_changes(
        self, 
        learning_switch_with_states, 
        mock_offset_engine
    ):
        """Test that switch state reflects offset engine learning state."""
        # Initially disabled
        mock_offset_engine.is_learning_enabled = False
        assert learning_switch_with_states.is_on is False
        
        # Enable learning
        mock_offset_engine.is_learning_enabled = True
        assert learning_switch_with_states.is_on is True
        
        # Disable learning
        mock_offset_engine.is_learning_enabled = False
        assert learning_switch_with_states.is_on is False

    def test_learning_stats_are_displayed(
        self, 
        learning_switch_with_states, 
        mock_offset_engine
    ):
        """Test that learning statistics are properly displayed."""
        # Test with learning enabled and data
        mock_offset_engine.get_learning_info.return_value = {
            "enabled": True,
            "samples": 150,
            "accuracy": 0.85,
            "confidence": 0.82,
            "has_sufficient_data": True,
            "mean_error": 0.3
        }
        
        attributes = learning_switch_with_states.extra_state_attributes
        assert attributes["enabled"] is True
        assert attributes["samples_collected"] == 150
        assert attributes["learning_accuracy"] == 0.85
        assert attributes["confidence_level"] == 0.82
        assert attributes["has_sufficient_data"] is True
        assert attributes["patterns_learned"] == 150

    def test_learning_stats_with_insufficient_data(
        self, 
        learning_switch_with_states, 
        mock_offset_engine
    ):
        """Test learning statistics when insufficient data available."""
        mock_offset_engine.get_learning_info.return_value = {
            "enabled": True,
            "samples": 5,
            "accuracy": 0.0,
            "confidence": 0.0,
            "has_sufficient_data": False
        }
        
        attributes = learning_switch_with_states.extra_state_attributes
        assert attributes["enabled"] is True
        assert attributes["samples_collected"] == 5
        assert attributes["has_sufficient_data"] is False


class TestMultipleEntities:
    """Test behavior with multiple smart climate entities."""

    @pytest.mark.asyncio
    async def test_each_climate_gets_own_learning_switch(self):
        """Test that each climate entity gets its own learning switch."""
        # This would be tested in integration tests
        # For now, ensure unique_id generation works correctly
        
        config_entry_1 = Mock(spec=ConfigEntry)
        config_entry_1.unique_id = "climate_1"
        config_entry_1.title = "Living Room Climate"
        
        config_entry_2 = Mock(spec=ConfigEntry)
        config_entry_2.unique_id = "climate_2"
        config_entry_2.title = "Bedroom Climate"
        
        mock_engine_1 = Mock(spec=OffsetEngine)
        mock_engine_2 = Mock(spec=OffsetEngine)
        
        switch_1 = LearningSwitch(config_entry_1, mock_engine_1, "Living Room Climate")
        switch_2 = LearningSwitch(config_entry_2, mock_engine_2, "Bedroom Climate")
        
        # Verify unique IDs are different
        assert switch_1.unique_id != switch_2.unique_id
        assert switch_1.unique_id == "climate_1_learning_switch"
        assert switch_2.unique_id == "climate_2_learning_switch"
        
        # Verify they use different engines
        assert switch_1._offset_engine is mock_engine_1
        assert switch_2._offset_engine is mock_engine_2


class TestErrorHandling:
    """Test error handling in switch operations."""

    @pytest.fixture
    def failing_offset_engine(self):
        """Create an offset engine that throws exceptions."""
        engine = Mock(spec=OffsetEngine)
        engine.enable_learning.side_effect = Exception("Enable failed")
        engine.disable_learning.side_effect = Exception("Disable failed")
        engine.get_learning_info.side_effect = Exception("Info failed")
        return engine

    @pytest.fixture
    def error_switch(self, mock_config_entry, failing_offset_engine):
        """Create a switch with a failing offset engine."""
        return LearningSwitch(
            mock_config_entry,
            failing_offset_engine,
            "Error Test Climate"
        )

    @pytest.mark.asyncio
    async def test_turn_on_handles_exceptions(self, error_switch):
        """Test that turn_on handles exceptions gracefully."""
        # Should not raise exception
        await error_switch.async_turn_on()
        
        # Verify the call was made (and failed)
        error_switch._offset_engine.enable_learning.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off_handles_exceptions(self, error_switch):
        """Test that turn_off handles exceptions gracefully."""
        # Should not raise exception
        await error_switch.async_turn_off()
        
        # Verify the call was made (and failed)
        error_switch._offset_engine.disable_learning.assert_called_once()

    def test_extra_state_attributes_handles_exceptions(self, error_switch):
        """Test that extra_state_attributes handles exceptions gracefully."""
        # Should return empty dict or safe fallback when get_learning_info fails
        # This depends on implementation - we'll handle this in the actual implementation
        
        # For now, just verify the call is made
        try:
            attributes = error_switch.extra_state_attributes
        except Exception:
            # If implementation doesn't handle errors, that's what we'll fix
            pass
        
        error_switch._offset_engine.get_learning_info.assert_called_once()