# Smart Climate v1.4.0-beta1 Release Notes

## 🚀 Major Feature: Thermal Efficiency System

**Target Energy Savings: 15-30%**

### Overview
v1.4.0-beta1 introduces an advanced thermal efficiency system that learns your home's thermal characteristics and optimizes HVAC runtime while maintaining comfort. This feature uses physics-based RC circuit modeling combined with machine learning to predict temperature drift and intelligently manage your climate control.

### Key Components

#### 6-State Thermal Management
The system operates through six intelligent states:
- **PRIMING**: Initial 24-hour learning phase for new users
- **DRIFTING**: Passive temperature monitoring when HVAC is off
- **CORRECTING**: Active boundary correction when approaching comfort limits
- **RECOVERY**: Post-correction stabilization (30 minutes)
- **PROBING**: Active thermal characteristic measurement
- **CALIBRATING**: System calibration based on probe results

#### Adaptive Comfort Bands
Dynamic comfort windows that adjust based on:
- User preference level (5 settings from MAX_COMFORT to MAX_SAVINGS)
- Outdoor temperature conditions
- Asymmetric heating/cooling behavior
- Extreme weather compensation

#### User Preference System
5 preference levels with intelligent behavior:
- **MAX_COMFORT** (±0.5°C): Tightest control, prioritizes comfort
- **COMFORT_PRIORITY** (±0.8°C): Comfort-focused with modest savings
- **BALANCED** (±1.2°C): Default balanced approach
- **SAVINGS_PRIORITY** (±1.8°C): Efficiency-focused operation
- **MAX_SAVINGS** (±2.5°C): Maximum energy savings

#### Physics-Based Thermal Modeling
- RC circuit thermal physics for accurate drift prediction
- Dual tau constants for asymmetric heating/cooling behavior
- Weighted learning from 5-probe history
- Confidence-based predictions

#### Smart Features
- **Shadow Mode**: Safe observation-only deployment (enabled by default)
- **Active/Passive Probes**: Intelligent thermal characteristic measurement
- **Cycle Health Monitoring**: Prevents excessive HVAC cycling
- **Weather-Aware Adjustments**: Adapts to extreme temperatures
- **AI Insights Engine**: Provides energy-saving recommendations

### Technical Implementation

#### State-Aware Learning Protocol
Prevents conflicts between ThermalManager and OffsetEngine:
- OffsetEngine pauses learning during thermal efficiency states
- Learns boundary corrections during CORRECTING phase
- Maintains data integrity across all operating modes

#### Comprehensive Testing
**420 tests implemented** across three phases:
- Phase 1: Foundation components (121 tests)
- Phase 2: State machine and learning (125 tests)
- Phase 3: Advanced features and insights (174 tests)

### Configuration

#### Enable Thermal Efficiency
```yaml
smart_climate:
  thermal_efficiency:
    enabled: true  # Default: false
    shadow_mode: true  # Default: true (observe only)
    preference_level: "BALANCED"  # Options: MAX_COMFORT, COMFORT_PRIORITY, BALANCED, SAVINGS_PRIORITY, MAX_SAVINGS
```

#### Preference Levels Detail

| Level | Comfort Band | Use Case | Expected Savings |
|-------|--------------|----------|------------------|
| MAX_COMFORT | ±0.5°C | Premium comfort, minimal temperature variation | 5-10% |
| COMFORT_PRIORITY | ±0.8°C | Comfort-focused with modest savings | 10-15% |
| BALANCED | ±1.2°C | Default balanced operation | 15-20% |
| SAVINGS_PRIORITY | ±1.8°C | Efficiency-focused, accepts more variation | 20-25% |
| MAX_SAVINGS | ±2.5°C | Maximum savings, wider temperature swings | 25-30% |

### Safety Features

#### Shadow Mode (Default)
- System observes and learns without controlling HVAC
- Provides insights and recommendations
- Allows verification before full deployment
- Can be disabled once confidence is established

#### Cycle Protection
- Minimum off time: 10 minutes
- Minimum on time: 5 minutes
- Prevents equipment damage from rapid cycling
- Health monitoring and reporting

### Home Assistant Integration

#### New Entities
- `sensor.smart_climate_thermal_state`: Current thermal state
- `sensor.smart_climate_thermal_confidence`: Model confidence (0-1)
- `sensor.smart_climate_energy_savings`: Estimated savings percentage
- `sensor.smart_climate_comfort_window`: Current comfort band
- `switch.smart_climate_shadow_mode`: Toggle shadow mode
- `select.smart_climate_preference_level`: Change preference level

#### Notifications
- Probe start/completion notifications
- Energy saving milestones
- System recommendations
- Thermal learning progress

### Migration Guide

#### From v1.3.x
1. Update via HACS or manual installation
2. Thermal efficiency is **disabled by default**
3. To enable:
   - Via UI: Settings → Integrations → Smart Climate → Configure
   - Enable "Thermal Efficiency"
   - Select preference level
   - Shadow mode is ON by default for safety
4. System enters PRIMING state for 24 hours
5. Monitor insights and recommendations
6. Disable shadow mode when ready for active control

### Performance Metrics

#### Expected Results
- **Energy Savings**: 15-30% reduction in HVAC runtime
- **Comfort Maintenance**: Temperature stays within user-defined bands
- **Learning Period**: 24-hour priming + 5 probe cycles for full optimization
- **Confidence Growth**: 0% → 80%+ within first week

### Known Limitations
- Requires consistent HVAC usage patterns for optimal learning
- Outdoor temperature sensor recommended for best results
- Initial 24-hour priming period before optimization begins
- Maximum effectiveness in moderate climates

### Troubleshooting

#### System Not Learning
- Verify HVAC is cycling regularly
- Check outdoor temperature sensor availability
- Ensure thermal efficiency is enabled
- Review logs for probe completion

#### Comfort Issues
- Adjust preference level for tighter control
- Check comfort band settings
- Verify shadow mode is disabled for active control
- Review cycle health metrics

### What's Next

#### v1.4.0 Stable Release
- Beta testing feedback incorporation
- Performance optimization
- Additional preference tuning
- Enhanced insights reporting

#### Future Enhancements
- Solar integration for optimal cooling timing
- Multi-zone coordination
- Predictive pre-cooling/heating
- Seasonal pattern learning

## Other Changes

### Bug Fixes
- Outlier detection configuration properly passed to OffsetEngine
- Improved error handling in extreme weather conditions
- Enhanced data persistence reliability

### Infrastructure
- Comprehensive test suite expanded to 420 tests
- Improved code organization with dedicated thermal modules
- Enhanced logging for thermal efficiency debugging

## Installation

### Via HACS (Recommended)
1. Open HACS
2. Search for "Smart Climate"
3. Update to v1.4.0-beta1
4. Restart Home Assistant

### Manual Installation
1. Download the latest release from GitHub
2. Copy `custom_components/smart_climate` to your `custom_components` directory
3. Restart Home Assistant

## Beta Testing

This is a **beta release** for testing the thermal efficiency feature. Please report issues at:
https://github.com/NexGenTech/smart-climate/issues

### Focus Areas for Testing
- Shadow mode observations vs actual comfort
- Energy savings measurements
- Preference level effectiveness
- Probe completion and learning
- State transitions and stability

## Acknowledgments

Special thanks to all contributors and beta testers who helped make this release possible.

---

**Full Changelog**: https://github.com/NexGenTech/smart-climate/compare/v1.3.1...v1.4.0-beta1

**Documentation**: https://github.com/NexGenTech/smart-climate/wiki/thermal-efficiency