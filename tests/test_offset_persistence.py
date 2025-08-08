"""Tests for OffsetEngine thermal persistence integration."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.data_store import SmartClimateDataStore


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    return MagicMock()


@pytest.fixture 
def mock_data_store():
    """Mock data store."""
    mock = AsyncMock(spec=SmartClimateDataStore)
    mock.async_save_learning_data = AsyncMock()
    mock.async_load_learning_data = AsyncMock()
    return mock


@pytest.fixture
def mock_thermal_data():
    """Sample thermal data for testing."""
    return {
        "version": "1.0",
        "state": {
            "current_state": "DRIFTING",
            "last_transition": "2025-08-08T15:45:00Z"
        },
        "model": {
            "tau_cooling": 95.5,
            "tau_warming": 148.2,
            "last_modified": "2025-08-08T15:30:00Z"
        },
        "probe_history": [
            {
                "tau_value": 95.5,
                "confidence": 0.85,
                "duration": 3600,
                "fit_quality": 0.92,
                "aborted": False,
                "timestamp": "2025-08-08T15:30:00Z"
            }
        ],
        "confidence": 0.75,
        "metadata": {
            "saves_count": 42,
            "corruption_recoveries": 0,
            "schema_version": "1.0"
        }
    }


@pytest.fixture
def basic_config():
    """Basic configuration for OffsetEngine."""
    return {
        "max_offset": 5.0,
        "ml_enabled": True,
        "enable_learning": False,
        "power_sensor": None
    }


class TestOffsetEngineThermalCallbacks:
    """Test thermal data callbacks integration."""
    
    def test_constructor_accepts_thermal_callbacks(self, basic_config):
        """Test constructor accepts optional thermal callback parameters."""
        get_thermal_cb = MagicMock()
        restore_thermal_cb = MagicMock()
        
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        
        # Verify callbacks are stored
        assert engine._get_thermal_data_cb is get_thermal_cb
        assert engine._restore_thermal_data_cb is restore_thermal_cb
    
    def test_constructor_works_without_thermal_callbacks(self, basic_config):
        """Test constructor works when thermal callbacks are not provided."""
        engine = OffsetEngine(config=basic_config)
        
        # Verify callbacks are None when not provided
        assert engine._get_thermal_data_cb is None
        assert engine._restore_thermal_data_cb is None


class TestOffsetEngineSaveWithThermalData:
    """Test save_learning_data with thermal data integration."""
    
    @pytest.mark.asyncio
    async def test_save_includes_thermal_data_when_callback_provided(
        self, basic_config, mock_data_store, mock_thermal_data
    ):
        """Test save operation includes thermal data when callback is provided."""
        get_thermal_cb = MagicMock(return_value=mock_thermal_data)
        restore_thermal_cb = MagicMock()
        
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        engine._data_store = mock_data_store
        
        # Execute save
        await engine.async_save_learning_data()
        
        # Verify callback was called
        get_thermal_cb.assert_called_once()
        
        # Verify save was called with thermal data
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        assert saved_data["version"] == "2.1"
        assert "thermal_data" in saved_data
        assert saved_data["thermal_data"] == mock_thermal_data
    
    @pytest.mark.asyncio
    async def test_save_excludes_thermal_data_when_no_callback(
        self, basic_config, mock_data_store
    ):
        """Test save operation works without thermal callbacks."""
        engine = OffsetEngine(config=basic_config)
        engine._data_store = mock_data_store
        
        # Execute save
        await engine.async_save_learning_data()
        
        # Verify save was called without thermal data
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        assert saved_data["version"] == "2.1"
        assert saved_data["thermal_data"] is None
    
    @pytest.mark.asyncio
    async def test_save_excludes_thermal_data_when_callback_returns_none(
        self, basic_config, mock_data_store
    ):
        """Test save operation handles None return from thermal callback."""
        get_thermal_cb = MagicMock(return_value=None)
        restore_thermal_cb = MagicMock()
        
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        engine._data_store = mock_data_store
        
        # Execute save
        await engine.async_save_learning_data()
        
        # Verify callback was called
        get_thermal_cb.assert_called_once()
        
        # Verify save was called without thermal data
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        assert saved_data["version"] == "2.1"
        assert saved_data["thermal_data"] is None
    
    @pytest.mark.asyncio
    async def test_save_continues_when_thermal_callback_fails(
        self, basic_config, mock_data_store
    ):
        """Test save operation continues when thermal callback raises exception."""
        get_thermal_cb = MagicMock(side_effect=Exception("Thermal data error"))
        restore_thermal_cb = MagicMock()
        
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        engine._data_store = mock_data_store
        
        # Execute save - should not raise exception
        await engine.async_save_learning_data()
        
        # Verify callback was called
        get_thermal_cb.assert_called_once()
        
        # Verify save was still called (thermal failure doesn't block save)
        mock_data_store.async_save_learning_data.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        
        assert saved_data["version"] == "2.1"
        assert saved_data["thermal_data"] is None


class TestOffsetEngineLoadWithThermalData:
    """Test load_learning_data with thermal data integration and migration."""
    
    @pytest.mark.asyncio
    async def test_load_calls_restore_callback_with_thermal_data(
        self, basic_config, mock_data_store, mock_thermal_data
    ):
        """Test load operation calls restore callback when thermal data exists."""
        get_thermal_cb = MagicMock()
        restore_thermal_cb = MagicMock()
        
        # Mock v2.1 data with thermal section
        mock_data_store.async_load_learning_data.return_value = {
            "version": "2.1",
            "learning_data": {"sample_count": 5},
            "thermal_data": mock_thermal_data
        }
        
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        engine._data_store = mock_data_store
        
        # Execute load
        result = await engine.async_load_learning_data()
        
        # Verify load succeeded
        assert result is True
        
        # Verify restore callback was called with thermal data
        restore_thermal_cb.assert_called_once_with(mock_thermal_data)
    
    @pytest.mark.asyncio
    async def test_load_skips_restore_when_no_thermal_data(
        self, basic_config, mock_data_store
    ):
        """Test load operation skips restore when no thermal data exists."""
        get_thermal_cb = MagicMock()
        restore_thermal_cb = MagicMock()
        
        # Mock v2.1 data without thermal section
        mock_data_store.async_load_learning_data.return_value = {
            "version": "2.1", 
            "learning_data": {"sample_count": 5},
            "thermal_data": None
        }
        
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        engine._data_store = mock_data_store
        
        # Execute load
        result = await engine.async_load_learning_data()
        
        # Verify load succeeded
        assert result is True
        
        # Verify restore callback was not called
        restore_thermal_cb.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_load_continues_when_restore_callback_fails(
        self, basic_config, mock_data_store, mock_thermal_data
    ):
        """Test load operation continues when restore callback raises exception."""
        get_thermal_cb = MagicMock()
        restore_thermal_cb = MagicMock(side_effect=Exception("Restore error"))
        
        # Mock v2.1 data with thermal section
        mock_data_store.async_load_learning_data.return_value = {
            "version": "2.1",
            "learning_data": {"sample_count": 5},
            "thermal_data": mock_thermal_data
        }
        
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        engine._data_store = mock_data_store
        
        # Execute load - should not raise exception
        result = await engine.async_load_learning_data()
        
        # Verify load still succeeded (restore failure doesn't block load)
        assert result is True
        
        # Verify restore callback was called
        restore_thermal_cb.assert_called_once_with(mock_thermal_data)
    
    @pytest.mark.asyncio 
    async def test_load_works_without_callbacks(
        self, basic_config, mock_data_store, mock_thermal_data
    ):
        """Test load operation works when no callbacks are provided."""
        # Mock v2.1 data with thermal section
        mock_data_store.async_load_learning_data.return_value = {
            "version": "2.1",
            "learning_data": {"sample_count": 5}, 
            "thermal_data": mock_thermal_data
        }
        
        engine = OffsetEngine(config=basic_config)
        engine._data_store = mock_data_store
        
        # Execute load - should work without callbacks
        result = await engine.async_load_learning_data()
        
        # Verify load succeeded
        assert result is True


class TestOffsetEngineMigration:
    """Test v1.0 to v2.1 migration logic."""
    
    @pytest.mark.asyncio
    async def test_migration_from_v1_to_v21(
        self, basic_config, mock_data_store
    ):
        """Test migration from version 1.0 to 2.1 format."""
        # Mock v1.0 data (old format - no version field, direct content)
        v1_data = {
            "sample_count": 10,
            "some_learning_data": "value"
        }
        mock_data_store.async_load_learning_data.return_value = v1_data
        
        engine = OffsetEngine(config=basic_config)
        engine._data_store = mock_data_store
        
        # Execute load
        result = await engine.async_load_learning_data()
        
        # Verify load succeeded
        assert result is True
        
        # Now trigger a save to verify migration
        await engine.async_save_learning_data()
        
        # Verify save was called with v2.1 structure
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data["version"] == "2.1"
        assert "learning_data" in saved_data
        assert saved_data["thermal_data"] is None
    
    @pytest.mark.asyncio
    async def test_migration_detects_v1_by_missing_version(
        self, basic_config, mock_data_store
    ):
        """Test migration correctly identifies v1.0 by missing version field."""
        # Mock v1.0 data (old format without version field)
        v1_data = {"engine_state": {"enable_learning": True}}
        mock_data_store.async_load_learning_data.return_value = v1_data
        
        engine = OffsetEngine(config=basic_config)
        engine._data_store = mock_data_store
        
        # Execute load
        result = await engine.async_load_learning_data()
        
        # Verify load succeeded
        assert result is True
        
        # Trigger save to verify migration
        await engine.async_save_learning_data()
        
        # Verify v2.1 structure was saved
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data["version"] == "2.1"
        assert "learning_data" in saved_data
        assert saved_data["thermal_data"] is None
    
    @pytest.mark.asyncio
    async def test_no_migration_for_v21_data(
        self, basic_config, mock_data_store
    ):
        """Test no migration occurs for already v2.1 data."""
        # Mock v2.1 data
        v21_data = {
            "version": "2.1",
            "learning_data": {"sample_count": 5},
            "thermal_data": None
        }
        mock_data_store.async_load_learning_data.return_value = v21_data
        
        engine = OffsetEngine(config=basic_config)
        engine._data_store = mock_data_store
        
        # Execute load
        result = await engine.async_load_learning_data()
        
        # Verify load succeeded
        assert result is True
        
        # Trigger save
        await engine.async_save_learning_data()
        
        # Verify structure remains v2.1 (no unnecessary migration)
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data["version"] == "2.1"


class TestCallbackIntegration:
    """Test callback integration with mock objects."""
    
    @pytest.mark.asyncio
    async def test_callback_execution_flow(self, basic_config, mock_data_store, mock_thermal_data):
        """Test complete flow of save with thermal data and load with restore."""
        get_thermal_cb = MagicMock(return_value=mock_thermal_data)
        restore_thermal_cb = MagicMock()
        
        # Create engine with callbacks
        engine = OffsetEngine(
            config=basic_config,
            get_thermal_data_cb=get_thermal_cb,
            restore_thermal_data_cb=restore_thermal_cb
        )
        engine._data_store = mock_data_store
        
        # First, save data
        await engine.async_save_learning_data()
        
        # Verify save included thermal data
        get_thermal_cb.assert_called_once()
        saved_data = mock_data_store.async_save_learning_data.call_args[0][0]
        assert saved_data["thermal_data"] == mock_thermal_data
        
        # Reset mocks
        get_thermal_cb.reset_mock()
        restore_thermal_cb.reset_mock()
        
        # Mock the load to return the saved data
        mock_data_store.async_load_learning_data.return_value = saved_data
        
        # Now load data
        result = await engine.async_load_learning_data()
        
        # Verify load succeeded and restore callback was called
        assert result is True
        restore_thermal_cb.assert_called_once_with(mock_thermal_data)
        get_thermal_cb.assert_not_called()  # Should not be called during load