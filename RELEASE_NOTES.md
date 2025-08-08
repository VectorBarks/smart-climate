# Release Notes

## v1.4.1-beta5 (2025-01-08)

### Summary
Cleanup release removing obsolete seasonal data migration code and fixing startup warnings.

### Bug Fixes
- 🐛 **Fixed SeasonalHysteresisLearner warning**: Removed obsolete `async_load()` calls that caused "object has no attribute" warnings during startup
- 🧹 **Removed unused migration code**: Cleaned up unnecessary migration logic for old seasonal_patterns.json files that never existed in production

### Technical Improvements  
- Simplified codebase by removing 25+ lines of obsolete migration code
- Seasonal data now properly loaded through unified storage system
- Cleaner startup logs without spurious warnings

### Known Status
- System confirmed working correctly in PRIMING state
- Thermal manager properly initializes with conservative defaults
- 93% ML accuracy observed in testing
- 36+ hysteresis cycles successfully tracked

### Compatibility
- Home Assistant 2024.1 or newer
- Python 3.11 or newer
- All features from v1.4.1-beta4 remain functional

---

# Release Notes - v1.0.0

## Smart Climate Control for Home Assistant - Initial Release

### Overview

Smart Climate Control v1.0.0 is now production-ready! This release provides intelligent temperature offset compensation for any Home Assistant climate device with inaccurate sensors.

### Key Features

- **Universal Compatibility**: Works with ANY Home Assistant climate entity
- **Intelligent Learning**: Lightweight ML system learns your AC's behavior patterns
- **Dynamic Offset Compensation**: Automatically adjusts for sensor inaccuracies
- **Multiple Operating Modes**: Normal, Away, Sleep, and Boost modes
- **User-Friendly Controls**: UI configuration and learning toggle switch
- **Data Persistence**: Learning patterns survive Home Assistant restarts

### Installation

**HACS (Recommended)**:
1. Add repository to HACS custom repositories
2. Install "Smart Climate Control"
3. Restart Home Assistant
4. Add integration via Settings → Devices & Services

**Manual**:
1. Copy `custom_components/smart_climate` to your `custom_components` folder
2. Restart Home Assistant
3. Add integration via Settings → Devices & Services

### Critical Fixes Included

- **Learning Data Collection**: Fixed feedback mechanism to properly collect learning samples
- **Offset Calculations**: Corrected inverted logic that caused AC to heat when it should cool
- **Sensor Handling**: Robust error handling for unavailable sensors
- **API Compatibility**: Updated for Home Assistant 2024.1+ compatibility

### Documentation

Comprehensive documentation is available in the `docs/` folder:
- Installation Guide
- Configuration Options
- Usage Instructions
- Learning System Explanation
- Troubleshooting Guide
- Architecture Overview

### Sensor Selection Tip

If your AC has switchable sensors, use the internal (exhaust) sensor for better results. The large, predictable offsets provide clearer signals for the learning system.

### Requirements

- Home Assistant 2024.1 or newer
- Python 3.11 or newer
- A climate entity to control
- A temperature sensor in the same room

### Known Limitations

- Single-point feedback sampling (enhancement planned for v1.1)
- Fixed feedback delays (adaptive delays coming in v1.1)
- Basic ML model (intentionally lightweight for efficiency)

### Next Steps

Please test the integration and provide feedback via GitHub Issues. Future enhancements planned for v1.1 include:
- Adaptive feedback delays
- Multi-point sampling
- AC temperature window detection
- Enhanced power monitoring integration

### Support

- Issues: https://github.com/VectorBarks/smart-climate/issues
- Discussions: https://github.com/VectorBarks/smart-climate/discussions

Thank you for using Smart Climate Control!