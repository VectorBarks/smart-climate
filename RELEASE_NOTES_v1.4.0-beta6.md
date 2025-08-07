# Release Notes - v1.4.0-beta6

**Release Date:** 2025-08-07  
**Type:** Critical Bug Fix Release

## 🔧 Critical Fix

### Thermal Efficiency Initialization Bug Fixed
**Issue:** Thermal efficiency features were not working despite being enabled in configuration
**Root Cause:** The SmartClimateCoordinator was not receiving thermal components during initialization
**Impact:** Users with thermal efficiency enabled would have the feature silently disabled
**Solution:** Modified climate.py to properly retrieve and pass thermal components to the coordinator

## Changes in This Release

### Bug Fixes
- **Fixed thermal component initialization** - Coordinator now properly receives thermal components from hass.data
- **Added debug logging** - Better visibility into thermal component initialization process
- **Improved error handling** - Graceful handling when thermal components are missing

### Technical Details
The fix ensures proper initialization flow:
1. Thermal components created in `__init__.py` 
2. Components stored in `hass.data[DOMAIN][entry_id]["thermal_components"][entity_id]`
3. `climate.py` now retrieves these components before creating the coordinator
4. Coordinator receives all thermal components and can properly initialize ThermalManager

## Testing Recommendations

After updating to beta6:
1. Restart Home Assistant
2. Check logs for: `"Retrieved thermal components for climate.[your_entity]: ['thermal_model', 'user_preferences', ...]"`
3. Verify `sensor.[your_entity]_thermal_status` exists in Developer Tools
4. Check climate entity attributes for `thermal_state`, `comfort_window`, etc.
5. With shadow mode enabled, monitor logs for thermal calculations

## Known Issues
- Issues #57-60: Hardcoded constants (technical debt - not affecting functionality)

## Upgrade Instructions
1. Download the latest release
2. Replace the `custom_components/smart_climate` folder
3. Restart Home Assistant
4. Verify thermal efficiency is working in logs

## What's Next
- Monitoring beta6 for stability
- Preparing for v1.4.0 stable release after user validation
- Future v1.5.0: Solar integration and multi-zone support

## Contributors
- @VectorBarks - Architecture and implementation
- Community testers - Bug reports and validation

---
*For questions or issues, please visit our [GitHub Issues](https://github.com/VectorBarks/smart-climate/issues) page.*