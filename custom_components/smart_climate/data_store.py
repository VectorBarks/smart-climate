"""Data persistence for Smart Climate Control learning data."""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Data format version
DATA_FORMAT_VERSION = "1.0"


def atomic_json_write(file_path: Path, data: Dict[str, Any]) -> None:
    """
    Atomically write JSON data to a file.

    Writes to a temporary file and then renames it to the final
    destination. Ensures durability by flushing data to disk.
    
    Args:
        file_path: Target file path for the JSON data
        data: Dictionary to save as JSON
        
    Raises:
        IOError: If file operations fail
        OSError: If filesystem operations fail
    """
    temp_path = file_path.with_suffix(f"{file_path.suffix}.tmp")
    try:
        # Write to the temporary file
        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            # Ensure data is written to the OS buffer
            f.flush()
            # Ensure data is written from the OS buffer to the disk
            os.fsync(f.fileno())

        # Atomically rename the temporary file to the final path
        temp_path.rename(file_path)
        _LOGGER.debug("Atomically wrote data to %s", file_path)

    except (IOError, OSError) as e:
        _LOGGER.error("Error during atomic write to %s: %s", file_path, e)
        # Clean up the temporary file if it still exists
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError as cleanup_err:
                _LOGGER.error("Error cleaning up temp file %s: %s", temp_path, cleanup_err)
        # Re-raise the exception so the caller knows the write failed
        raise


class SmartClimateDataStore:
    """Thread-safe data store for Smart Climate learning data persistence."""
    
    def __init__(self, hass: HomeAssistant, entity_id: str):
        """Initialize the data store for a specific climate entity.
        
        Args:
            hass: Home Assistant instance
            entity_id: Climate entity ID (e.g., "climate.living_room")
        """
        self._hass = hass
        self._entity_id = entity_id
        self._lock = asyncio.Lock()  # Prevents concurrent writes to the same file
        
        # Calculate data file path
        self._data_file_path = self.get_data_file_path()
        
        _LOGGER.debug(
            "SmartClimateDataStore initialized for %s, file: %s",
            entity_id, self._data_file_path
        )
    
    def get_data_file_path(self) -> Path:
        """Get the file path for storing learning data.
        
        Returns:
            Path object for the JSON data file
        """
        # Convert entity ID to safe filename
        safe_entity_id = re.sub(r'[^\w\-_.]', '_', self._entity_id.replace(".", "_"))
        filename = f"smart_climate_learning_{safe_entity_id}.json"
        
        # Store in Home Assistant's .storage directory
        storage_dir = Path(self._hass.config.config_dir) / ".storage"
        return storage_dir / filename
    
    def _ensure_data_directory(self) -> None:
        """Ensure the data directory exists."""
        self._data_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _create_backup_if_needed(self, file_path: Path) -> None:
        """Create a backup of existing file before overwriting.
        
        Args:
            file_path: File to backup
        """
        if file_path.exists():
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            try:
                # Copy to backup (don't use move to keep original during write)
                import shutil
                shutil.copy2(file_path, backup_path)
                _LOGGER.debug("Created backup: %s", backup_path)
            except (IOError, OSError) as e:
                _LOGGER.warning("Failed to create backup %s: %s", backup_path, e)
    
    async def async_save_learning_data(self, learning_data: Dict[str, Any]) -> None:
        """Save learning data to JSON file safely and asynchronously.
        
        Args:
            learning_data: Dictionary containing learning patterns and statistics
        """
        async with self._lock:
            try:
                # Prepare data structure with metadata
                save_data = {
                    "version": DATA_FORMAT_VERSION,
                    "entity_id": self._entity_id,
                    "last_updated": datetime.now().isoformat(),
                    "learning_enabled": True,
                    "learning_data": learning_data
                }
                
                # Ensure directory exists
                await self._hass.async_add_executor_job(self._ensure_data_directory)
                
                # Create backup if file exists
                await self._hass.async_add_executor_job(
                    self._create_backup_if_needed, self._data_file_path
                )
                
                # Perform atomic write
                await self._hass.async_add_executor_job(
                    atomic_json_write, self._data_file_path, save_data
                )
                
                _LOGGER.debug(
                    "Saved learning data for %s (%d bytes)",
                    self._entity_id, self._data_file_path.stat().st_size
                )
                
            except Exception as e:
                _LOGGER.error(
                    "Failed to save learning data for %s: %s",
                    self._entity_id, e
                )
    
    async def async_load_learning_data(self) -> Optional[Dict[str, Any]]:
        """Load learning data from JSON file safely and asynchronously.
        
        Returns:
            Learning data dictionary on success, None on failure or if file not found
        """
        def _load_sync() -> Optional[Dict[str, Any]]:
            """Synchronous load operation for executor."""
            if not self._data_file_path.exists():
                _LOGGER.debug("No learning data file found for %s", self._entity_id)
                return None
            
            try:
                with self._data_file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Validate data structure
                if not isinstance(data, dict):
                    _LOGGER.warning("Invalid data format in %s: not a dictionary", self._data_file_path)
                    return None
                
                # Check version compatibility
                version = data.get("version", "unknown")
                if version != DATA_FORMAT_VERSION:
                    _LOGGER.warning(
                        "Unsupported data version %s in %s (expected %s)",
                        version, self._data_file_path, DATA_FORMAT_VERSION
                    )
                    return None
                
                # Validate entity ID matches
                saved_entity_id = data.get("entity_id")
                if saved_entity_id != self._entity_id:
                    _LOGGER.warning(
                        "Entity ID mismatch in %s: saved=%s, expected=%s",
                        self._data_file_path, saved_entity_id, self._entity_id
                    )
                    return None
                
                # Extract learning data
                learning_data = data.get("learning_data")
                if not isinstance(learning_data, dict):
                    _LOGGER.warning("Missing or invalid learning_data in %s", self._data_file_path)
                    return None
                
                _LOGGER.debug(
                    "Loaded learning data for %s (%d bytes)",
                    self._entity_id, self._data_file_path.stat().st_size
                )
                
                return learning_data
                
            except json.JSONDecodeError as e:
                _LOGGER.warning(
                    "Corrupted JSON in %s: %s - starting with fresh data",
                    self._data_file_path, e
                )
                return None
                
            except (IOError, OSError) as e:
                _LOGGER.error(
                    "Error loading learning data from %s: %s",
                    self._data_file_path, e
                )
                return None
        
        # Use lock to prevent reading during write operations
        async with self._lock:
            return await self._hass.async_add_executor_job(_load_sync)