# Release Notes - v1.4.3-beta1

## 🎯 Opportunistic Calibration System

This release replaces the fixed 2am calibration hour with intelligent stability detection, making calibration more flexible and effective.

## ✨ Major Features

### Opportunistic Calibration
- **Automatic Detection**: System now detects stable conditions automatically (30+ minutes idle, <0.3°C drift)
- **No Fixed Schedule**: Removed the hardcoded 2am calibration hour
- **Manual Control**: New "Force Calibration" button for immediate calibration
- **Realistic Defaults**: Updated drift threshold from unrealistic 0.1°C to practical 0.3°C

### Configuration Updates
- **Removed**: `calibration_hour` option (breaking change)
- **Added**: `calibration_idle_minutes` (15-120 minutes, default: 30)
- **Added**: `calibration_drift_threshold` (0.1-1.0°C, default: 0.3)
- **Building Guidance**: UI now suggests appropriate thresholds for different building types

## 🔧 Technical Improvements

### StabilityDetector
- New component tracks AC idle duration and temperature drift
- Uses 10-minute sliding window for drift calculation
- Configurable thresholds for different building types

### Button Platform
- Added Force Calibration button entity
- Integrates with thermal state machine
- Respects state constraints (blocks during probing)

## 📊 Threshold Recommendations

Based on Gemini consultation for realistic building physics:
- **Modern/Well-Insulated Homes**: 0.2-0.3°C drift threshold
- **Standard Homes**: 0.4-0.5°C drift threshold
- **Older/Drafty Buildings**: 0.6-1.0°C drift threshold

## 🐛 Bug Fixes

- Fixed thermal state sensor not updating when state changes
- Fixed AttributeError in DriftingState handler
- Fixed thermal persistence callback not triggering
- Improved AC state detection from power consumption

## 💔 Breaking Changes

- **Removed `calibration_hour` configuration option**
  - Existing configs will automatically migrate
  - Calibration now happens opportunistically, not at fixed times

## 📝 Configuration Migration

If you had `calibration_hour` set, it will be automatically removed. The new system will calibrate whenever stable conditions are detected, which is more effective than a fixed schedule.

## 🔄 Upgrade Instructions

1. Update via HACS or manually copy files
2. Restart Home Assistant
3. Check configuration options - adjust drift threshold if needed:
   - Use 0.2-0.3°C for well-insulated homes
   - Use 0.4-0.5°C for standard homes
   - Use 0.6-1.0°C for older buildings
4. Optional: Use Force Calibration button to trigger immediate calibration

## 📈 Testing

- Added 18 new test files with comprehensive coverage
- All existing tests pass
- TDD methodology used throughout implementation

## 🔮 Next Steps

- Microclimate correction implementation
- Enhanced UI dashboard improvements
- Additional sensor optimizations

---

**Full Changelog**: [v1.4.2-beta5...v1.4.3-beta1](https://github.com/VectorBarks/smart-climate/compare/v1.4.2-beta5...v1.4.3-beta1)

**Contributors**: Smart Climate Development Team

**Special Thanks**: Gemini AI for building physics consultation on realistic drift thresholds