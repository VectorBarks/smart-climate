# Release Notes - v1.5.0-alpha1

## 🎯 Passive Thermal Learning During PRIMING

This alpha release introduces **passive thermal learning** - the system now learns your home's thermal characteristics during the PRIMING state by monitoring natural AC cycles, eliminating the 24-48 hour "do nothing" period.

## ✨ New Features

### Passive Learning System
- **Automatic Thermal Characterization**: Learns tau values by analyzing temperature drift when AC turns off naturally
- **Non-Intrusive**: No active probing required - uses normal AC operation patterns
- **Exponential Curve Fitting**: Advanced mathematical analysis extracts thermal time constants from drift data
- **Configurable Thresholds**: Adjust sensitivity for your specific building characteristics

## 🔧 Technical Improvements

### Core Components
- **New `thermal_utils.py`**: Mathematical engine for exponential decay analysis using scipy
- **Extended `StabilityDetector`**: Now tracks HVAC states with 4-hour rolling history
- **Enhanced `ThermalManager`**: Orchestrates passive learning during PRIMING state
- **Updated `Coordinator`**: Feeds real-time HVAC state data to learning system

### Configuration Options
- `passive_learning_enabled`: Enable/disable passive learning (default: true)
- `passive_min_drift_minutes`: Minimum drift duration for valid measurements (10-30 min, default: 15)
- `passive_confidence_threshold`: Minimum confidence to accept results (0.2-0.5, default: 0.3)

## 📊 Performance Characteristics

- **Confidence Levels**: Passive measurements: 0.3-0.5, Active probing: 0.7-0.9
- **Minimum Data**: 10+ temperature points over 15+ minutes
- **Tau Bounds**: 300-86,400 seconds (5 min to 24 hours)
- **Processing Time**: <100ms for curve fitting analysis
- **Memory Usage**: 240 entries max in history buffer (4 hours)

## 🧪 Testing

- **54 new tests** added across all components
- Mathematical functions: 13 tests
- Drift detection: 11 tests  
- Orchestration: 18 tests
- Integration: 12 tests
- All existing tests still passing

## 🔄 Compatibility

- **Backward Compatible**: No breaking changes
- **Graceful Degradation**: Falls back to default tau values if scipy unavailable
- **Auto-Activation**: Works immediately for new installations in PRIMING state
- **Migration-Free**: No data migration required

## 📝 Known Limitations

- Requires scipy for curve fitting (optional dependency)
- Needs at least 15 minutes of continuous AC off time for analysis
- Lower confidence than active probing (by design)

## 🚀 Installation

1. Download the release package
2. Copy to `custom_components/smart_climate/`
3. Restart Home Assistant
4. Passive learning activates automatically during PRIMING

## 📋 Changelog

### Added
- Passive thermal learning during PRIMING state
- Exponential curve fitting for tau extraction
- HVAC state tracking in StabilityDetector
- Configuration options for passive learning thresholds
- Comprehensive test coverage for new functionality

### Changed
- PRIMING state now actively learns instead of waiting
- StabilityDetector extended with drift detection capabilities
- ThermalManager includes passive learning orchestration
- Coordinator feeds HVAC state data continuously

### Fixed
- PRIMING state no longer wastes 24-48 hours doing nothing
- Thermal characteristics learned even without active probing

## 🏷️ Version Info

- **Version**: 1.5.0-alpha1
- **Type**: Alpha Pre-release
- **Branch**: feature/passive-learning-priming
- **Commit**: 0a17085
- **Home Assistant**: 2024.1.0+
- **Python**: 3.11+

## ⚠️ Alpha Release Notice

This is an alpha release for testing purposes. While all tests pass, please monitor system behavior and report any issues. Not recommended for production use without thorough testing in your environment.

## 🐛 Bug Reports

Please report issues at: https://github.com/VectorBarks/smart-climate/issues

Include:
- Home Assistant version
- Smart Climate version
- Debug logs with `smart_climate: debug`
- Description of observed behavior