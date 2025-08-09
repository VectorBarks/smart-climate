# Smart Climate Control Documentation

Welcome to the Smart Climate Control documentation hub. This integration brings intelligent temperature management to your Home Assistant setup by learning your AC's unique behavior and automatically optimizing comfort and efficiency.

## Table of Contents

### Quick Start
- [Installation Guide](installation-guide.md) - Complete setup instructions for HACS and manual installation
- [User Guide](user-guide.md) - Day-to-day usage, modes, and features overview

### Configuration
- [Configuration Guide](configuration-guide.md) - All settings, power thresholds, and optimization options
- [Sensor Reference](sensor-reference.md) - Complete sensor documentation and placement guide

### Technical Reference  
- [Technical Reference](technical-reference.md) - Architecture, algorithms, and advanced features

## Project Overview

**Smart Climate Control** is a Home Assistant custom integration that wraps your existing climate entities with intelligent offset learning and thermal management. Instead of relying on your AC's internal temperature sensor (which is often inaccurate), it uses your room's actual temperature sensor to calculate precise offsets and maintain your desired comfort level.

## Key Features

### 🧠 Machine Learning
- **Lightweight Learning System**: <1ms predictions with <1MB memory usage
- **Pattern Recognition**: Learns time-of-day, outdoor temperature, and power state correlations
- **Hysteresis Learning**: Understands your AC's start/stop temperature windows (with power monitoring)
- **Seasonal Adaptation**: Adapts to changing outdoor conditions over time

### 🌡️ Thermal Efficiency
- **Shadow Mode**: Safe learning phase that observes without controlling
- **6-State Thermal Management**: PRIMING → DRIFTING → CORRECTING → RECOVERY → PROBING → CALIBRATING
- **RC Physics Model**: Learns your room's cooling/warming time constants (tau values)
- **Thermal Preferences**: 5 comfort levels from MAX_COMFORT to MAX_SAVINGS

### 🌤️ Weather Integration
- **Predictive Pre-cooling**: Heat wave and clear sky strategies
- **Forecast Integration**: Uses Home Assistant weather entities
- **Thermal Mass Utilization**: Pre-cools building before extreme conditions

### 📊 Comprehensive Monitoring
- **47 Sensors**: Dashboard metrics, learning progress, system health, thermal state
- **Real-time Analytics**: Accuracy tracking, confidence scoring, performance metrics
- **One-Click Dashboard**: Generate complete visualization with single service call

### ⚡ Advanced Features
- **Adaptive Delays**: Learns optimal feedback timing for your HVAC
- **Outlier Detection**: Modified Z-score + MAD filtering for robust data
- **Gradual Adjustments**: Configurable rate limiting (0.1-2.0°C per update)
- **Power State Detection**: Idle/minimum/maximum consumption thresholds

## Version Highlights

### v1.4.1-beta5 (Latest)
- Removed obsolete seasonal migration code
- Fixed async_load warnings
- Shadow mode behavior improvements
- Thermal efficiency enhancements

### v1.3.0 Features
- Weather forecast integration with pre-cooling strategies
- Adaptive feedback delay learning
- Seasonal pattern adaptation
- Enhanced power threshold configuration

### v1.2.0 Features
- Automatic dashboard sensor creation
- One-click dashboard generation service
- Comprehensive visualization setup

## Quick Feature Matrix

| Feature | Basic Setup | With Power Sensor | With Weather | Full Setup |
|---------|-------------|-------------------|--------------|------------|
| Offset Learning | ✅ | ✅ | ✅ | ✅ |
| Time Patterns | ✅ | ✅ | ✅ | ✅ |
| Hysteresis Learning | ❌ | ✅ | ✅ | ✅ |
| Weather Strategies | ❌ | ❌ | ✅ | ✅ |
| Thermal Efficiency | ✅ | ✅ | ✅ | ✅ |
| Seasonal Adaptation | ❌ | ❌ | ❌ | ✅* |

*Requires outdoor sensor

## Getting Started

1. **Install** using [HACS](installation-guide.md#hacs-installation) (recommended)
2. **Configure** through the UI with your climate entity and room sensor
3. **Learn** about [daily usage patterns](user-guide.md#basic-operation)
4. **Optimize** with [advanced configuration options](configuration-guide.md)
5. **Monitor** progress through the [sensor dashboard](sensor-reference.md)

## System Requirements

- Home Assistant 2024.1 or newer
- Python 3.11 or newer  
- Existing climate device (AC, heat pump, etc.)
- Room temperature sensor
- Optional: Outdoor sensor, power monitor, weather integration

## Architecture Highlights

Smart Climate Control is built on a modular, fail-safe architecture:
- **Separation of Concerns**: Each component has a single responsibility
- **Dependency Injection**: Improves testability and reduces coupling
- **Graceful Degradation**: Continues working even when components fail
- **Performance Optimized**: <1ms predictions, efficient memory usage

## Support & Community

- **Documentation**: Complete guides for all features and use cases
- **GitHub Issues**: Bug reports and feature requests
- **Home Assistant Community**: Discussion and user support
- **Release Notes**: Detailed changelog and migration guides

## What Makes It Different

Unlike simple thermostat replacements, Smart Climate Control:
- **Learns Your Specific AC**: Every unit behaves differently
- **Uses Physics-Based Models**: RC thermal models, not just statistical averages  
- **Preserves Original Functionality**: Wraps existing entities without breaking anything
- **Provides Deep Insights**: 47 sensors reveal system behavior and performance
- **Optimizes Continuously**: Improves comfort and efficiency over time

## Next Steps

Choose your path based on your needs:

**New Users**: Start with [Installation Guide](installation-guide.md) → [User Guide](user-guide.md)

**Existing Users**: Explore [Configuration Guide](configuration-guide.md) for optimization tips

**Advanced Users**: Dive into [Technical Reference](technical-reference.md) for architecture details

**Troubleshooting**: Check sensor status in [Sensor Reference](sensor-reference.md)

---

*Smart Climate Control v1.4.1-beta5 - Bringing intelligence to your climate control*