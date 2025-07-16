# Smart Climate Control v1.3.9-beta1 Release Notes

## 🚨 CRITICAL ARCHITECTURAL FIX: Options Flow Configuration

### **Major Issue Resolved**
Fixed a critical architectural bug where **all options flow settings were being ignored** by the climate entity. This affected virtually every configurable setting in the integration.

### **Root Cause**
The climate entity was only reading `config_entry.data` (initial setup) and completely ignoring `config_entry.options` (user configuration changes made through the "Configure" button).

### **Technical Fix**
**File**: `custom_components/smart_climate/climate.py`
**Line**: 2858
**Change**: 
```python
# Before (broken):
config = config_entry.data

# After (fixed):
config = {**config_entry.data, **config_entry.options}
```

### **Settings Now Working Properly**

This single fix resolves configuration issues for **20+ settings**:

#### **Core Temperature Settings**
- ✅ Maximum temperature offset (1-10°C)
- ✅ Minimum temperature limit (10-25°C)
- ✅ Maximum temperature limit (20-35°C)
- ✅ Default target temperature (16-30°C)

#### **System Behavior**
- ✅ Update interval (30-600 seconds)
- ✅ Machine learning enabled/disabled
- ✅ Learning system enabled/disabled
- ✅ Gradual adjustment rate (0.1-2.0°C)
- ✅ Feedback delay (10-300 seconds)

#### **Mode-Specific Settings**
- ✅ Away mode temperature (10-35°C)
- ✅ Sleep mode offset (-5 to +5°C)
- ✅ Boost mode offset (-10 to 0°C)

#### **Retry & Timeout Settings**
- ✅ Retry mechanism enabled/disabled
- ✅ Maximum retry attempts (1-10)
- ✅ Initial timeout (30-300 seconds)
- ✅ Save interval (300+ seconds)

#### **Weather & Predictive Features**
- ✅ Weather forecast enabled/disabled
- ✅ Weather entity selection
- ✅ Heat wave strategy settings
- ✅ Clear sky strategy settings
- ✅ Temperature thresholds and timing

#### **Power Management**
- ✅ Power idle threshold
- ✅ Power active threshold

### **User Impact**

**Before this fix:**
- Configuration changes through "Configure" button were saved but ignored
- Only initial setup values were used
- Users thought features were broken or non-functional

**After this fix:**
- All configuration changes now take effect immediately after Home Assistant restart
- Temperature limits are properly enforced
- Mode-specific settings work correctly
- Weather integration functions as configured
- Retry mechanisms and timeouts work properly

### **Installation**

1. **HACS**: Update through HACS repository
2. **Manual**: Download and replace files
3. **Restart Home Assistant** (required for configuration changes to take effect)

### **Verification**

After restart, verify that:
1. Weather integration shows enabled if configured
2. Temperature limits are enforced
3. Away/Sleep/Boost modes use configured values
4. Update intervals match your settings
5. ML and learning toggles work properly

### **Breaking Changes**
None - this is a pure bug fix that makes existing configuration settings work as intended.

### **Compatibility**
- Home Assistant 2024.1+
- Python 3.11+
- All existing configurations remain valid

---

**This release resolves what was likely the most significant configuration bug in the Smart Climate integration. Users who experienced non-functional features should find them working correctly after this update.**

## Previous Release Notes
- v1.3.1-beta8: Complete dashboard sensor system
- v1.3.1-beta7: HVACMode import compatibility fix
- v1.3.0: Multi-layered intelligence system