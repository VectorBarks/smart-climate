# Smart Climate Control v1.3.1-beta7 Release Notes

## 🚨 Critical Compatibility Fix: HVACMode Import

This is a **critical hotfix release** that resolves Home Assistant integration loading issues affecting users on current HA versions.

### The Problem

Users were experiencing integration load failures with the error:
```
ImportError: cannot import name HVACMode from homeassistant.const
```

This prevented the Smart Climate integration from loading entirely, making it inaccessible in Home Assistant.

### Root Cause

The issue was caused by deprecated import paths in `delay_learner.py` that referenced `homeassistant.const` for the `HVACMode` enum. Home Assistant moved this enum to `homeassistant.components.climate.const` in recent versions, breaking the import.

### The Fix

**v1.3.1-beta7** resolves this by:

- ✅ **Updated Import Paths**: Changed imports to use current Home Assistant API location
- ✅ **Comprehensive Testing**: Added 66 new tests covering import compatibility and integration loading
- ✅ **Future-Proof**: Uses current Home Assistant patterns to prevent similar issues
- ✅ **Zero User Impact**: No configuration changes required - automatic compatibility fix

### Technical Changes

#### Core Fix
- **Updated** `delay_learner.py`: Changed `from homeassistant.const import HVACMode` to `from homeassistant.components.climate.const import HVACMode`
- **Updated** test imports to match current API patterns
- **Added** comprehensive integration loading tests

#### New Test Coverage
- **4 tests** validating HVACMode accessibility from proper import location
- **62 tests** covering integration loading scenarios and platform setup
- **100% pass rate** ensuring compatibility with current Home Assistant versions

### User Impact

#### Immediate Benefits
- **✅ Integration Loads Successfully**: No more ImportError preventing integration access
- **✅ Zero Configuration**: Fix applies automatically after update - no user action needed
- **✅ Full Functionality**: All existing features work properly once integration loads
- **✅ Current HA Compatibility**: Works with latest Home Assistant versions

#### Who Should Update
- **All Users**: This fix affects everyone using Smart Climate on current Home Assistant versions
- **Priority**: High - Integration won't load without this fix on newer HA versions
- **Urgency**: Update immediately if experiencing integration loading issues

### Installation

**Via HACS (Recommended)**:
1. Go to HACS → Integrations
2. Find "Smart Climate Control" 
3. Enable "Show beta versions" in HACS settings
4. Update to v1.3.1-beta7
5. Restart Home Assistant

**Manual Installation**:
1. Download v1.3.1-beta7 from GitHub releases
2. Extract to `custom_components/smart_climate/`
3. Restart Home Assistant

### Verification

After updating and restarting:

1. **Check Integration Status**:
   - Go to Settings → Devices & Services
   - Verify "Smart Climate Control" appears and loads without errors

2. **Verify Functionality**:
   - Confirm your Smart Climate entities are available
   - Check entity attributes are populated correctly
   - Test basic temperature adjustment functionality

3. **Monitor Logs**:
   - Should see no ImportError messages related to HVACMode
   - Integration should load cleanly without compatibility warnings

### Compatibility

- **Home Assistant**: 2024.1+ (including latest versions)
- **Python**: 3.11+
- **Backward Compatibility**: Fully maintained - all existing configurations preserved
- **Feature Compatibility**: All v1.3.1-beta6 features unchanged and functional

### What's Next

This hotfix ensures the integration loads properly. All existing features from v1.3.1-beta6 remain:

- ✅ HVAC mode filtering (fixes temperature adjustments in fan_only/off modes)
- ✅ Learning data poisoning prevention
- ✅ Weather configuration structure fixes
- ✅ Complete entity attributes visibility
- ✅ All v1.3.0 advanced features (adaptive delays, weather integration, seasonal learning)

### Support

If you experience issues after updating:

1. **Check Logs**: Look for any remaining import errors or loading issues
2. **Restart Again**: Sometimes requires a second restart after major fixes
3. **Report Issues**: Create GitHub issue with HA version and specific error messages

**GitHub Repository**: https://github.com/VectorBarks/smart-climate  
**Issues**: https://github.com/VectorBarks/smart-climate/issues

### Thank You

Thanks to the community for reporting compatibility issues quickly. This fix ensures Smart Climate continues working reliably across all supported Home Assistant versions.

---

## Complete Changelog

For full details of all changes in the v1.3.1 series, see [CHANGELOG.md](CHANGELOG.md).

**Previous Releases**:
- v1.3.1-beta6: HVAC mode filtering and learning data protection
- v1.3.1-beta5: Weather configuration structure fix  
- v1.3.1-beta4: Entity attributes visibility fix
- v1.3.1-beta1: Critical stability and data safety fixes
- v1.3.0: Advanced intelligence features (adaptive delays, weather integration, seasonal learning)