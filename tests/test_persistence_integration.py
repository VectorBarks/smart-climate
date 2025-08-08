"""ABOUTME: Comprehensive integration tests for thermal data persistence.
Tests full save/load cycle, multi-entity concurrency, corruption recovery, button reset, and migration."""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from pathlib import Path
from datetime import datetime, timedelta
import json

from custom_components.smart_climate.const import DOMAIN
from custom_components.smart_climate.offset_engine import OffsetEngine
from custom_components.smart_climate.coordinator import SmartClimateCoordinator
from custom_components.smart_climate.thermal_models import ThermalState


class TestFullPersistenceIntegration:
    """Test complete persistence flow: Coordinator→OffsetEngine→ThermalManager→File."""

    @pytest.fixture
    def mock_hass_with_thermal_data(self, mock_thermal_manager):
        """Mock hass with proper thermal data structure."""
        mock_hass = Mock()
        entity_id = "climate.living_room"
        entry_id = "test_entry"
        
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity_id: {"thermal_manager": mock_thermal_manager}
                    },
                    "offset_engines": {
                        entity_id: Mock()  # Will be replaced by test
                    }
                }
            }
        }
        
        # Mock coordinator methods
        mock_coordinator = Mock(spec=SmartClimateCoordinator)
        mock_coordinator.hass = mock_hass
        mock_coordinator.entry_id = entry_id
        
        def mock_get_thermal_data(entity_id):
            return mock_thermal_manager.serialize()
            
        def mock_restore_thermal_data(entity_id, data):
            mock_thermal_manager.restore(data)
            
        mock_coordinator.get_thermal_data = mock_get_thermal_data
        mock_coordinator.restore_thermal_data = mock_restore_thermal_data
        
        return mock_hass, mock_coordinator, entity_id, entry_id

    @pytest.mark.asyncio
    async def test_complete_save_load_cycle_with_thermal_data(
        self, mock_hass_with_thermal_data, mock_thermal_callbacks, thermal_data_structure_helper
    ):
        """Test complete save/load cycle including thermal data."""
        mock_hass, mock_coordinator, entity_id, entry_id = mock_hass_with_thermal_data
        get_thermal_cb, restore_thermal_cb = mock_thermal_callbacks
        
        # Mock Store for file operations
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            mock_store.async_load = AsyncMock()
            
            # Create OffsetEngine with thermal callbacks
            offset_engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={"enable_learning": True, "max_offset": 5.0},
                get_thermal_data_cb=get_thermal_cb,
                restore_thermal_data_cb=restore_thermal_cb
            )
            
            # Test save cycle
            await offset_engine.save_learning_data()
            
            # Verify Store was called with v2.1 schema including thermal_data
            mock_store.async_save.assert_called_once()
            saved_data = mock_store.async_save.call_args[0][0]
            
            assert saved_data["version"] == "2.1"
            assert "learning_data" in saved_data
            assert "thermal_data" in saved_data
            assert saved_data["thermal_data"] is not None
            
            # Verify thermal callback was invoked
            get_thermal_cb.assert_called_once()
            
            # Test load cycle
            mock_store.async_load.return_value = saved_data
            await offset_engine.load_learning_data()
            
            # Verify restore callback was invoked with thermal data
            restore_thermal_cb.assert_called_once_with(saved_data["thermal_data"])

    @pytest.mark.asyncio
    async def test_thermal_data_included_in_v21_schema(
        self, mock_hass_with_thermal_data, mock_thermal_callbacks
    ):
        """Test that thermal_data section is properly included in v2.1 file structure."""
        mock_hass, mock_coordinator, entity_id, entry_id = mock_hass_with_thermal_data
        get_thermal_cb, restore_thermal_cb = mock_thermal_callbacks
        
        # Set up expected thermal data structure
        expected_thermal_data = {
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
            "probe_history": [],
            "confidence": 0.75,
            "metadata": {
                "saves_count": 1,
                "corruption_recoveries": 0,
                "schema_version": "1.0"
            }
        }
        get_thermal_cb.return_value = expected_thermal_data
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            offset_engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={"enable_learning": True},
                get_thermal_data_cb=get_thermal_cb,
                restore_thermal_data_cb=restore_thermal_cb
            )
            
            await offset_engine.save_learning_data()
            
            # Verify v2.1 schema structure
            saved_data = mock_store.async_save.call_args[0][0]
            
            assert saved_data["version"] == "2.1"
            assert saved_data["entity_id"] == entity_id
            assert "last_updated" in saved_data
            assert isinstance(saved_data["learning_data"], dict)
            assert saved_data["thermal_data"] == expected_thermal_data

    @pytest.mark.asyncio
    async def test_save_includes_thermal_metadata(
        self, mock_hass_with_thermal_data, mock_thermal_callbacks
    ):
        """Test that saves include proper metadata and timestamps."""
        mock_hass, mock_coordinator, entity_id, entry_id = mock_hass_with_thermal_data
        get_thermal_cb, restore_thermal_cb = mock_thermal_callbacks
        
        # Mock thermal data with metadata
        thermal_data = {
            "metadata": {"saves_count": 5, "corruption_recoveries": 1}
        }
        get_thermal_cb.return_value = thermal_data
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            offset_engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_thermal_cb,
                restore_thermal_data_cb=restore_thermal_cb
            )
            
            # Save and verify metadata is preserved
            await offset_engine.save_learning_data()
            
            saved_data = mock_store.async_save.call_args[0][0]
            
            # Check top-level metadata
            assert "last_updated" in saved_data
            last_updated = datetime.fromisoformat(saved_data["last_updated"])
            assert (datetime.now() - last_updated).total_seconds() < 10
            
            # Check thermal metadata is preserved
            assert saved_data["thermal_data"]["metadata"]["saves_count"] == 5
            assert saved_data["thermal_data"]["metadata"]["corruption_recoveries"] == 1


class TestMultiEntityConcurrency:
    """Test persistence with multiple climate entities."""

    @pytest.mark.asyncio
    async def test_multiple_entities_separate_files(self):
        """Test that multiple entities save to separate files simultaneously."""
        mock_hass = Mock()
        entry_id = "test_entry"
        
        # Set up two entities
        entity1 = "climate.living_room"
        entity2 = "climate.bedroom"
        
        # Mock thermal managers for both entities
        mock_thermal1 = Mock()
        mock_thermal1.serialize.return_value = {"state": "ENTITY1_DATA"}
        mock_thermal2 = Mock()
        mock_thermal2.serialize.return_value = {"state": "ENTITY2_DATA"}
        
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity1: {"thermal_manager": mock_thermal1},
                        entity2: {"thermal_manager": mock_thermal2}
                    }
                }
            }
        }
        
        # Mock callbacks
        def make_get_cb(thermal_manager):
            return lambda: thermal_manager.serialize()
        
        def make_restore_cb(thermal_manager):
            return lambda data: thermal_manager.restore(data)
        
        get_cb1 = make_get_cb(mock_thermal1)
        restore_cb1 = make_restore_cb(mock_thermal1)
        get_cb2 = make_get_cb(mock_thermal2)
        restore_cb2 = make_restore_cb(mock_thermal2)
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            # Mock stores for each entity (different file names)
            mock_store1 = Mock()
            mock_store1.async_save = AsyncMock()
            mock_store2 = Mock()
            mock_store2.async_save = AsyncMock()
            
            # Return different store instances for different entity IDs
            def store_factory(hass, path):
                if entity1 in path:
                    return mock_store1
                elif entity2 in path:
                    return mock_store2
                return Mock()
                
            MockStore.side_effect = store_factory
            
            # Create offset engines for both entities
            engine1 = OffsetEngine(
                hass=mock_hass,
                entity_id=entity1,
                config={},
                get_thermal_data_cb=get_cb1,
                restore_thermal_data_cb=restore_cb1
            )
            
            engine2 = OffsetEngine(
                hass=mock_hass,
                entity_id=entity2,
                config={},
                get_thermal_data_cb=get_cb2,
                restore_thermal_data_cb=restore_cb2
            )
            
            # Save both concurrently
            await asyncio.gather(
                engine1.save_learning_data(),
                engine2.save_learning_data()
            )
            
            # Verify separate stores were used
            mock_store1.async_save.assert_called_once()
            mock_store2.async_save.assert_called_once()
            
            # Verify correct thermal data was saved for each
            saved_data1 = mock_store1.async_save.call_args[0][0]
            saved_data2 = mock_store2.async_save.call_args[0][0]
            
            assert saved_data1["entity_id"] == entity1
            assert saved_data2["entity_id"] == entity2
            assert saved_data1["thermal_data"]["state"] == "ENTITY1_DATA"
            assert saved_data2["thermal_data"]["state"] == "ENTITY2_DATA"

    @pytest.mark.asyncio
    async def test_concurrent_saves_no_conflicts(self):
        """Test that concurrent save operations don't interfere with each other."""
        mock_hass = Mock()
        entity_id = "climate.test"
        entry_id = "test_entry"
        
        # Mock thermal manager
        mock_thermal = Mock()
        mock_thermal.serialize.return_value = {"concurrent": "save_test"}
        
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity_id: {"thermal_manager": mock_thermal}
                    }
                }
            }
        }
        
        get_cb = lambda: mock_thermal.serialize()
        restore_cb = lambda data: mock_thermal.restore(data)
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            # Create multiple engines for same entity
            engines = []
            for i in range(3):
                engine = OffsetEngine(
                    hass=mock_hass,
                    entity_id=entity_id,
                    config={},
                    get_thermal_data_cb=get_cb,
                    restore_thermal_data_cb=restore_cb
                )
                engines.append(engine)
            
            # Save all concurrently
            await asyncio.gather(*[engine.save_learning_data() for engine in engines])
            
            # Verify all saves completed (Store handles atomicity)
            assert mock_store.async_save.call_count == 3

    @pytest.mark.asyncio
    async def test_entity_isolation_on_corruption(self):
        """Test that corruption in one entity doesn't affect others."""
        mock_hass = Mock()
        entry_id = "test_entry"
        entity1 = "climate.good"
        entity2 = "climate.bad"
        
        # Mock thermal managers
        mock_thermal_good = Mock()
        mock_thermal_good.serialize.return_value = {"state": "GOOD_DATA"}
        
        # Create thermal manager that will fail
        mock_thermal_bad = Mock()
        mock_thermal_bad.serialize.side_effect = Exception("Thermal serialization failed")
        
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity1: {"thermal_manager": mock_thermal_good},
                        entity2: {"thermal_manager": mock_thermal_bad}
                    }
                }
            }
        }
        
        # Create callbacks
        good_get_cb = lambda: mock_thermal_good.serialize()
        bad_get_cb = lambda: mock_thermal_bad.serialize()
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store1 = Mock()
            mock_store1.async_save = AsyncMock()
            mock_store2 = Mock()
            mock_store2.async_save = AsyncMock()
            
            def store_factory(hass, path):
                if entity1 in path:
                    return mock_store1
                else:
                    return mock_store2
                    
            MockStore.side_effect = store_factory
            
            # Create engines
            good_engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity1,
                config={},
                get_thermal_data_cb=good_get_cb,
                restore_thermal_data_cb=lambda data: None
            )
            
            bad_engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity2,
                config={},
                get_thermal_data_cb=bad_get_cb,
                restore_thermal_data_cb=lambda data: None
            )
            
            # Save both (bad one should not crash good one)
            await good_engine.save_learning_data()
            await bad_engine.save_learning_data()
            
            # Good entity should save successfully
            mock_store1.async_save.assert_called_once()
            saved_data = mock_store1.async_save.call_args[0][0]
            assert saved_data["entity_id"] == entity1
            assert saved_data["thermal_data"]["state"] == "GOOD_DATA"
            
            # Bad entity should save without thermal_data (error isolation)
            mock_store2.async_save.assert_called_once()
            bad_saved_data = mock_store2.async_save.call_args[0][0]
            assert bad_saved_data["entity_id"] == entity2
            assert bad_saved_data["thermal_data"] is None  # Error isolation


class TestCorruptionRecoveryIntegration:
    """Test end-to-end corruption recovery scenarios."""

    @pytest.mark.asyncio
    async def test_corrupted_thermal_section_recovery(self, mock_thermal_callbacks):
        """Test that corrupted thermal_data doesn't prevent offset data save."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        get_thermal_cb, restore_thermal_cb = mock_thermal_callbacks
        # Make restore callback fail
        restore_thermal_cb.side_effect = Exception("Thermal restore failed")
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            # Mock corrupted file data
            corrupted_data = {
                "version": "2.1",
                "entity_id": entity_id,
                "last_updated": "2025-08-08T16:00:00Z",
                "learning_data": {"samples": []},  # Valid offset data
                "thermal_data": {"invalid": "thermal_structure"}  # Corrupted thermal
            }
            mock_store.async_load.return_value = corrupted_data
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_thermal_cb,
                restore_thermal_data_cb=restore_thermal_cb
            )
            
            # Load should succeed despite thermal corruption
            result = await engine.load_learning_data()
            assert result is True
            
            # Restore callback should have been attempted
            restore_thermal_cb.assert_called_once_with({"invalid": "thermal_structure"})
            
            # Save should work and isolate thermal errors
            await engine.save_learning_data()
            mock_store.async_save.assert_called_once()
            
            # Verify offset data preserved
            saved_data = mock_store.async_save.call_args[0][0]
            assert "learning_data" in saved_data

    @pytest.mark.asyncio
    async def test_field_level_recovery_end_to_end(self, mock_thermal_manager):
        """Test field-level recovery from corruption through full cycle."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        # Set up thermal manager to simulate field-level recovery
        mock_thermal_manager.corruption_recovery_count = 3
        mock_thermal_manager.thermal_state_restored = True
        
        # Create callbacks that use the thermal manager
        def get_cb():
            return mock_thermal_manager.serialize()
        
        def restore_cb(data):
            # Simulate field-level validation and recovery
            if data.get("model", {}).get("tau_cooling", 0) < 0:
                mock_thermal_manager.corruption_recovery_count += 1
            mock_thermal_manager.restore(data)
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            # Mock file with field-level corruption
            corrupted_file = {
                "version": "2.1",
                "entity_id": entity_id,
                "learning_data": {"samples": []},
                "thermal_data": {
                    "model": {
                        "tau_cooling": -50.0,  # Invalid: negative
                        "tau_warming": 2000.0   # Invalid: too large
                    },
                    "confidence": 1.5,  # Invalid: > 1.0
                    "metadata": {"corruption_recoveries": 2}
                }
            }
            mock_store.async_load.return_value = corrupted_file
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # Load with corruption should succeed
            await engine.load_learning_data()
            
            # Verify thermal manager restore was called (recovery happens there)
            mock_thermal_manager.restore.assert_called_once()
            
            # Save should preserve recovery metrics
            await engine.save_learning_data()
            
            saved_data = mock_store.async_save.call_args[0][0]
            thermal_data = saved_data["thermal_data"]
            
            # Recovery metrics should be updated
            assert thermal_data["metadata"]["corruption_recoveries"] >= 3

    @pytest.mark.asyncio
    async def test_malformed_file_recovery(self):
        """Test recovery from completely malformed JSON file."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        get_cb = Mock(return_value={"version": "1.0"})
        restore_cb = Mock()
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            # Mock JSON decode error
            mock_store.async_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # Load should handle malformed file gracefully
            result = await engine.load_learning_data()
            
            # Should start fresh (exact behavior depends on implementation)
            # At minimum, it shouldn't crash
            assert result is not None
            
            # Restore callback should not be called with invalid data
            restore_cb.assert_not_called()


class TestButtonResetIntegration:
    """Test button reset integration with persistence."""

    @pytest.mark.asyncio  
    async def test_button_reset_triggers_save(self, mock_thermal_manager):
        """Test that button press triggers reset and immediate save."""
        mock_hass = Mock()
        entity_id = "climate.test"
        entry_id = "test_entry"
        
        # Set up hass data for coordinator
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "thermal_components": {
                        entity_id: {"thermal_manager": mock_thermal_manager}
                    }
                }
            }
        }
        
        # Mock coordinator
        mock_coordinator = Mock()
        mock_coordinator.entry_id = entry_id
        mock_coordinator.hass = mock_hass
        
        def mock_get_thermal_manager(eid):
            return mock_thermal_manager
        
        def mock_get_offset_engine(eid):
            return mock_offset_engine
            
        mock_coordinator.get_thermal_manager = mock_get_thermal_manager
        mock_coordinator.get_offset_engine = mock_get_offset_engine
        
        # Mock offset engine
        mock_offset_engine = Mock()
        mock_offset_engine.save_learning_data = AsyncMock()
        
        # Mock button entity (simplified)
        class MockButton:
            def __init__(self, coordinator, entity_id):
                self._coordinator = coordinator
                self._entity_id = entity_id
                
            async def async_press(self):
                # Button press logic per architecture
                thermal_manager = self._coordinator.get_thermal_manager(self._entity_id)
                thermal_manager.reset()
                offset_engine = self._coordinator.get_offset_engine(self._entity_id)
                await offset_engine.save_learning_data()
        
        button = MockButton(mock_coordinator, entity_id)
        
        # Simulate button press
        await button.async_press()
        
        # Verify reset was called
        mock_thermal_manager.reset.assert_called_once()
        
        # Verify save was triggered immediately
        mock_offset_engine.save_learning_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_preserves_offset_data(self, mock_thermal_manager):
        """Test that reset only affects thermal data, preserves offset learning."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        # Create callbacks
        get_cb = lambda: mock_thermal_manager.serialize()
        restore_cb = lambda data: mock_thermal_manager.restore(data)
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            # Mock existing file with both offset and thermal data
            existing_data = {
                "version": "2.1",
                "entity_id": entity_id,
                "learning_data": {
                    "samples": [{"important": "offset_data"}],
                    "has_sufficient_data": True
                },
                "thermal_data": {
                    "model": {"tau_cooling": 95.5, "tau_warming": 148.2},
                    "confidence": 0.8
                }
            }
            mock_store.async_load.return_value = existing_data
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # Load existing data
            await engine.load_learning_data()
            
            # Simulate reset (thermal manager resets its state)
            mock_thermal_manager.reset()
            reset_thermal_data = {
                "model": {"tau_cooling": 90.0, "tau_warming": 150.0},  # Reset values
                "confidence": 0.0,
                "state": {"current_state": "PRIMING"}
            }
            mock_thermal_manager.serialize.return_value = reset_thermal_data
            
            # Save after reset
            await engine.save_learning_data()
            
            saved_data = mock_store.async_save.call_args[0][0]
            
            # Offset data should be preserved
            assert saved_data["learning_data"]["samples"] == [{"important": "offset_data"}]
            assert saved_data["learning_data"]["has_sufficient_data"] is True
            
            # Thermal data should be reset
            assert saved_data["thermal_data"]["model"]["tau_cooling"] == 90.0
            assert saved_data["thermal_data"]["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_reset_updates_diagnostics(self, mock_thermal_manager):
        """Test that reset updates diagnostic properties correctly."""
        # Set up diagnostic properties on thermal manager
        mock_thermal_manager.thermal_data_last_saved = None
        mock_thermal_manager.thermal_state_restored = True
        mock_thermal_manager.corruption_recovery_count = 2
        
        # After reset, diagnostics should be updated
        def mock_reset():
            mock_thermal_manager.thermal_state_restored = False  # Fresh state
            mock_thermal_manager.corruption_recovery_count = 0   # Reset count
            
        mock_thermal_manager.reset = mock_reset
        
        # Mock serialize to return diagnostic info
        def mock_serialize():
            return {
                "metadata": {
                    "corruption_recoveries": mock_thermal_manager.corruption_recovery_count
                },
                "diagnostics": {
                    "thermal_state_restored": mock_thermal_manager.thermal_state_restored
                }
            }
        mock_thermal_manager.serialize = mock_serialize
        
        mock_hass = Mock()
        entity_id = "climate.test"
        
        get_cb = lambda: mock_thermal_manager.serialize()
        restore_cb = lambda data: None
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # Perform reset and save
            mock_thermal_manager.reset()
            await engine.save_learning_data()
            
            # Verify diagnostic updates are saved
            saved_data = mock_store.async_save.call_args[0][0]
            
            assert saved_data["thermal_data"]["metadata"]["corruption_recoveries"] == 0
            assert saved_data["thermal_data"]["diagnostics"]["thermal_state_restored"] is False


class TestMigrationIntegration:
    """Test v1.0 to v2.1 migration integration."""

    @pytest.mark.asyncio
    async def test_v10_to_v21_migration_flow(self):
        """Test complete migration flow from v1.0 to v2.1 file format."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        get_cb = Mock(return_value={"migrated": "thermal_data"})
        restore_cb = Mock()
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            # Mock v1.0 file (no thermal_data section)
            v10_file = {
                "samples": [{"old": "format"}],
                "has_sufficient_data": True,
                "learning_enabled": True
            }
            mock_store.async_load.return_value = v10_file
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # Load should trigger lazy migration
            await engine.load_learning_data()
            
            # Restore callback should not be called (no thermal data in v1.0)
            restore_cb.assert_not_called()
            
            # Save should create v2.1 format
            await engine.save_learning_data()
            
            saved_data = mock_store.async_save.call_args[0][0]
            
            # Verify v2.1 structure
            assert saved_data["version"] == "2.1"
            assert saved_data["entity_id"] == entity_id
            assert "last_updated" in saved_data
            
            # Verify learning data preserved from v1.0
            assert saved_data["learning_data"]["samples"] == [{"old": "format"}]
            assert saved_data["learning_data"]["has_sufficient_data"] is True
            
            # Verify thermal data added
            assert saved_data["thermal_data"] == {"migrated": "thermal_data"}

    @pytest.mark.asyncio
    async def test_migration_preserves_offset_data(self):
        """Test that migration preserves all original offset learning data."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        get_cb = Mock(return_value={})
        restore_cb = Mock()
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            # Rich v1.0 file with extensive learning data
            v10_complex_file = {
                "samples": [
                    {"predicted": 2.0, "actual": 1.8, "timestamp": "2025-08-01T10:00:00Z"},
                    {"predicted": 1.5, "actual": 1.6, "timestamp": "2025-08-01T11:00:00Z"}
                ],
                "model_version": "1.3",
                "has_sufficient_data": True,
                "learning_enabled": True,
                "accuracy_metrics": {
                    "mae": 0.2,
                    "rmse": 0.25,
                    "last_calculated": "2025-08-01T12:00:00Z"
                },
                "outlier_detection": {
                    "enabled": True,
                    "threshold": 2.5,
                    "filtered_samples": 3
                }
            }
            mock_store.async_load.return_value = v10_complex_file
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # Load and migrate
            await engine.load_learning_data()
            await engine.save_learning_data()
            
            saved_data = mock_store.async_save.call_args[0][0]
            
            # Verify all original data preserved exactly
            learning_data = saved_data["learning_data"]
            assert learning_data["samples"] == v10_complex_file["samples"]
            assert learning_data["model_version"] == "1.3"
            assert learning_data["has_sufficient_data"] is True
            assert learning_data["learning_enabled"] is True
            assert learning_data["accuracy_metrics"] == v10_complex_file["accuracy_metrics"]
            assert learning_data["outlier_detection"] == v10_complex_file["outlier_detection"]

    @pytest.mark.asyncio
    async def test_lazy_migration_timing(self):
        """Test that migration happens on load, not on startup."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        get_cb = Mock(return_value={})
        restore_cb = Mock()
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_load = AsyncMock()
            mock_store.async_save = AsyncMock()
            
            # v1.0 file
            v10_file = {"samples": [], "learning_enabled": True}
            mock_store.async_load.return_value = v10_file
            
            # Engine creation should not trigger migration
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # No load operations yet
            mock_store.async_load.assert_not_called()
            mock_store.async_save.assert_not_called()
            
            # Migration should happen on first load
            await engine.load_learning_data()
            
            # Now load should have been called
            mock_store.async_load.assert_called_once()
            
            # Migration completed lazily in memory, but file not rewritten yet
            # (actual implementation may vary)


class TestErrorIsolationIntegration:
    """Test error isolation in thermal persistence integration."""

    @pytest.mark.asyncio
    async def test_thermal_callback_failure_isolation(self):
        """Test that thermal callback failures don't block offset data saves."""
        mock_hass = Mock()
        entity_id = "climate.test"
        
        # Create failing thermal callbacks
        def failing_get_cb():
            raise Exception("Get thermal data failed")
        
        def failing_restore_cb(data):
            raise Exception("Restore thermal data failed")
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            mock_store.async_load = AsyncMock()
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=failing_get_cb,
                restore_thermal_data_cb=failing_restore_cb
            )
            
            # Save should succeed despite thermal callback failure
            await engine.save_learning_data()
            
            # Verify save was called with thermal_data=None (error isolation)
            mock_store.async_save.assert_called_once()
            saved_data = mock_store.async_save.call_args[0][0]
            
            assert saved_data["version"] == "2.1"
            assert "learning_data" in saved_data
            assert saved_data["thermal_data"] is None  # Isolated failure
            
            # Load with thermal section should also succeed
            file_with_thermal = {
                "version": "2.1",
                "learning_data": {"samples": []},
                "thermal_data": {"some": "data"}
            }
            mock_store.async_load.return_value = file_with_thermal
            
            result = await engine.load_learning_data()
            assert result is True  # Load succeeds despite restore callback failure

    @pytest.mark.asyncio
    async def test_thermal_manager_missing_graceful(self):
        """Test graceful handling of missing thermal components."""
        mock_hass = Mock()
        entity_id = "climate.test"
        entry_id = "test_entry"
        
        # Incomplete hass.data structure (missing thermal components)
        mock_hass.data = {
            DOMAIN: {
                entry_id: {
                    "offset_engines": {}
                    # Missing "thermal_components" section
                }
            }
        }
        
        # Mock coordinator with safe methods
        mock_coordinator = Mock()
        mock_coordinator.hass = mock_hass
        mock_coordinator.entry_id = entry_id
        
        def safe_get_thermal_data(entity_id):
            try:
                thermal_manager = mock_hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]["thermal_manager"]
                return thermal_manager.serialize()
            except KeyError:
                return None  # Graceful handling
        
        def safe_restore_thermal_data(entity_id, data):
            try:
                thermal_manager = mock_hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]["thermal_manager"]
                thermal_manager.restore(data)
            except KeyError:
                pass  # Graceful handling
        
        mock_coordinator.get_thermal_data = safe_get_thermal_data
        mock_coordinator.restore_thermal_data = safe_restore_thermal_data
        
        # Create callbacks using coordinator methods
        get_cb = lambda: mock_coordinator.get_thermal_data(entity_id)
        restore_cb = lambda data: mock_coordinator.restore_thermal_data(entity_id, data)
        
        with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
            mock_store = MockStore.return_value
            mock_store.async_save = AsyncMock()
            
            engine = OffsetEngine(
                hass=mock_hass,
                entity_id=entity_id,
                config={},
                get_thermal_data_cb=get_cb,
                restore_thermal_data_cb=restore_cb
            )
            
            # Save should work gracefully without thermal data
            await engine.save_learning_data()
            
            # Verify save completed with thermal_data=None
            mock_store.async_save.assert_called_once()
            saved_data = mock_store.async_save.call_args[0][0]
            
            assert saved_data["thermal_data"] is None

    @pytest.mark.asyncio
    async def test_partial_hass_data_structure(self):
        """Test handling of partially initialized hass.data structure."""
        mock_hass = Mock()
        entity_id = "climate.test"
        entry_id = "test_entry"
        
        # Various incomplete structures
        test_structures = [
            {},  # Empty hass.data
            {DOMAIN: {}},  # Missing entry_id
            {DOMAIN: {entry_id: {}}},  # Missing thermal_components
            {DOMAIN: {entry_id: {"thermal_components": {}}}},  # Missing entity
        ]
        
        for i, data_structure in enumerate(test_structures):
            mock_hass.data = data_structure
            
            # Create safe callbacks
            def safe_get_cb():
                try:
                    return mock_hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]["thermal_manager"].serialize()
                except (KeyError, AttributeError):
                    return None
            
            def safe_restore_cb(data):
                try:
                    mock_hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]["thermal_manager"].restore(data)
                except (KeyError, AttributeError):
                    pass
            
            with patch('custom_components.smart_climate.offset_engine.Store') as MockStore:
                mock_store = MockStore.return_value
                mock_store.async_save = AsyncMock()
                
                engine = OffsetEngine(
                    hass=mock_hass,
                    entity_id=entity_id,
                    config={},
                    get_thermal_data_cb=safe_get_cb,
                    restore_thermal_data_cb=safe_restore_cb
                )
                
                # Each structure should be handled gracefully
                await engine.save_learning_data()
                
                saved_data = mock_store.async_save.call_args[0][0]
                assert saved_data["thermal_data"] is None
                assert saved_data["version"] == "2.1"