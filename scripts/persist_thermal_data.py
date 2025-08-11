#!/usr/bin/env python3
"""
Script to extract and persist in-memory thermal calibration data from Home Assistant.

This script can be run via Home Assistant's Python Scripts integration or 
directly in the Developer Tools > Services as a python_script.

Usage:
1. Copy this script to your Home Assistant config/python_scripts/ folder
2. Call service: python_script.persist_thermal_data
3. Or run in Developer Tools > Template:
   {% set ns = namespace(found=false) %}
   ... (the script logic)
"""

import json
import logging
from datetime import datetime
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

def persist_thermal_data_from_memory(hass):
    """
    Extract in-memory thermal data and persist it to disk.
    
    This function accesses the Home Assistant data store to find
    ThermalManager instances and triggers their persistence.
    """
    
    results = []
    domain = "smart_climate"
    
    try:
        # Check if smart_climate domain exists in hass.data
        if domain not in hass.data:
            _LOGGER.warning("Smart Climate domain not found in hass.data")
            return {"error": "Smart Climate not loaded"}
        
        # Iterate through all config entries
        for entry_id, entry_data in hass.data[domain].items():
            _LOGGER.info(f"Checking entry: {entry_id}")
            
            # Look for thermal components
            thermal_components = entry_data.get("thermal_components", {})
            if not thermal_components:
                _LOGGER.info(f"No thermal components in entry {entry_id}")
                continue
                
            # Look for offset engines (they handle persistence)
            offset_engines = entry_data.get("offset_engines", {})
            
            # Process each entity
            for entity_id, components in thermal_components.items():
                _LOGGER.info(f"Processing entity: {entity_id}")
                
                # Get the ThermalManager
                thermal_manager = components.get("thermal_manager")
                if not thermal_manager:
                    _LOGGER.warning(f"No ThermalManager for {entity_id}")
                    continue
                
                # Get current state info
                current_state = getattr(thermal_manager, '_current_state', None)
                last_transition = getattr(thermal_manager, '_last_transition', None)
                
                state_info = {
                    "entity_id": entity_id,
                    "current_state": current_state.value if current_state else "unknown",
                    "last_transition": last_transition.isoformat() if last_transition else None
                }
                
                # Check if this entity transitioned through calibrating
                if current_state and current_state.value in ['calibrating', 'drifting']:
                    _LOGGER.info(f"Entity {entity_id} has calibration data (state: {current_state.value})")
                    
                    # Get the OffsetEngine for this entity
                    offset_engine = offset_engines.get(entity_id)
                    if offset_engine:
                        try:
                            # Trigger immediate save
                            _LOGGER.info(f"Triggering immediate save for {entity_id}")
                            
                            # Call the synchronous save method if available
                            if hasattr(offset_engine, 'save_learning_data'):
                                # This is a sync method, we need to make it work
                                import asyncio
                                
                                # Get or create event loop
                                try:
                                    loop = asyncio.get_event_loop()
                                except RuntimeError:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                
                                # Create async wrapper
                                async def save_data():
                                    if hasattr(offset_engine, 'async_save_learning_data'):
                                        await offset_engine.async_save_learning_data()
                                        return True
                                    else:
                                        # Fallback to sync version
                                        offset_engine.save_learning_data()
                                        return True
                                
                                # Run the save
                                if loop.is_running():
                                    # Schedule as task if loop is already running
                                    task = asyncio.create_task(save_data())
                                    state_info["save_scheduled"] = True
                                else:
                                    # Run directly if no loop running
                                    result = loop.run_until_complete(save_data())
                                    state_info["save_completed"] = result
                                
                                _LOGGER.info(f"Save triggered for {entity_id}")
                                
                            # Also check if we can get the thermal data directly
                            if thermal_manager:
                                # Get thermal model data
                                thermal_model = getattr(thermal_manager, '_model', None)
                                if thermal_model:
                                    tau_cooling = getattr(thermal_model, '_tau_cooling', 90.0)
                                    tau_warming = getattr(thermal_model, '_tau_warming', 150.0)
                                    
                                    state_info["thermal_model"] = {
                                        "tau_cooling": tau_cooling,
                                        "tau_warming": tau_warming
                                    }
                                    
                                    _LOGGER.info(f"Thermal model data: tau_cooling={tau_cooling}, tau_warming={tau_warming}")
                                
                                # Check for any calibration data
                                calibration_hour = getattr(thermal_manager, 'calibration_hour', 2)
                                state_info["calibration_hour"] = calibration_hour
                                
                        except Exception as e:
                            _LOGGER.error(f"Error saving data for {entity_id}: {e}")
                            state_info["error"] = str(e)
                    else:
                        _LOGGER.warning(f"No OffsetEngine found for {entity_id}")
                        state_info["error"] = "No OffsetEngine"
                
                results.append(state_info)
        
        # Log summary
        _LOGGER.info(f"Processed {len(results)} entities")
        for result in results:
            _LOGGER.info(f"Entity {result['entity_id']}: state={result.get('current_state')}, "
                        f"saved={result.get('save_completed', False)}")
        
        return {
            "success": True,
            "entities_processed": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        _LOGGER.error(f"Error in persist_thermal_data_from_memory: {e}", exc_info=True)
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


# For Home Assistant python_script service
if 'hass' in globals():
    result = persist_thermal_data_from_memory(hass)
    # Store result in hass.data for retrieval
    hass.data["persist_thermal_result"] = result
    logger.info(f"Thermal data persistence result: {result}")