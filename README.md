# Smart Climate Control for Home Assistant

[![Version](https://img.shields.io/badge/Version-1.3.0-brightgreen.svg)](https://github.com/VectorBarks/smart-climate/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

Transform any climate device with inaccurate sensors into an intelligent, ML-powered climate control system with predictive algorithms and adaptive learning.

## The Problem

Many AC units and heat pumps have poorly placed internal temperature sensors that don't reflect actual room temperature. This creates thermal feedback loops and control instability, leading to uncomfortable spaces and wasted energy as the unit can't accurately maintain your desired temperature.

## The Solution

Smart Climate Control creates a virtual climate entity that:
- Uses your accurate room sensor instead of the AC's internal sensor
- Dynamically calculates temperature offsets using multi-factor algorithms
- Learns environmental patterns through hysteresis detection and exponential smoothing
- Predicts optimal adjustments using weather forecasts and seasonal adaptation
- Maintains your desired comfort level with sub-degree precision

## Key Features

**NEW in v1.3.0: Advanced Predictive Intelligence**
- **Adaptive Feedback Delays**: ML-powered optimization of AC response timing based on temperature stability patterns
  - Exponential moving average smoothing of learned delays with 70% weight on recent measurements
  - Temperature stability detection with 0.1°C threshold monitoring
  - Automatic timeout protection and graceful fallback to conservative defaults
- **Weather Forecast Integration**: Proactive temperature adjustments using outdoor weather pattern analysis
  - Heat wave pre-cooling strategies with -1.0°C offset during rising temperature trends
  - Clear sky thermal optimization for energy-efficient temperature maintenance
  - Strategy evaluation system with 30-minute throttling to prevent API overload
- **Seasonal Adaptation**: Context-aware hysteresis learning using outdoor temperature buckets
  - 45-day pattern retention with temperature bucket matching (5°C tolerance)
  - Outdoor temperature-based pattern correlation for seasonal accuracy
  - Graceful fallback to global patterns when insufficient seasonal data available

**NEW in v1.2.1-beta2: Learning Data Preservation Fix**
- Fixed learning data loss when learning switch is disabled before restart (Issue #25)
- All accumulated learning samples are now preserved even when learning is temporarily disabled
- Both save and load operations now handle learner data regardless of enable_learning state

**Fixed in v1.2.1-beta1: Critical Bug Fixes**
- Fixed AC continuing to cool/heat when room temperature reaches target (Issue #22)
- Fixed dashboard service blocking I/O warnings (Issue #18)
- Fixed crashes when wrapped entity becomes unavailable (Issue #19)
- Fixed deprecated ApexCharts span properties in dashboard (Issue #20)
- Room temperature deviation check prevents overcooling/overheating
- Automatic recovery when entities come back online
- Dashboard service now fully asynchronous

**v1.2.0: Smart Climate Dashboard & Enhanced Learning**
- Beautiful visualization dashboard for learning progress and system performance
- Automatic sensor creation - no manual configuration needed
- One-click dashboard generation service
- Immediate temperature adjustments on Home Assistant startup
- Real confidence progression (0-100%) instead of stuck at 50%
- Configurable save intervals (5 minutes to 24 hours) with 60-minute default
- Enhanced save diagnostics visible in Home Assistant UI
- Robust startup retry mechanism for slow sensor initialization

**v1.1.0: HysteresisLearner - AC Temperature Window Detection**
- Automatically learns your AC's start/stop temperature thresholds
- Understands when your AC actually turns on and off
- Adapts predictions based on real power consumption patterns
- Dramatically improves temperature control accuracy
- Works seamlessly with power monitoring sensors

**Universal Compatibility**
- Works with ANY Home Assistant climate entity
- Compatible with ANY temperature sensor
- No device-specific limitations
- Configurable default target temperature (16-30°C)

**Intelligent Learning System**
- Multi-layered learning architecture: reactive offset calculation + predictive strategies + seasonal adaptation
- HysteresisLearner with power consumption correlation for AC cycle detection
- Exponential smoothing algorithms for pattern recognition and noise reduction
- Logarithmic confidence scaling with condition diversity factors
- Time-series pattern analysis for circadian and seasonal temperature correlations
- Real-time learning state monitoring with <1ms prediction latency
- Persistent JSON storage with atomic backup safety and schema versioning

**Smart Operation**
- Hybrid control system: immediate rule-based responses with background ML optimization
- Configurable gradual adjustment rates (0.1-2.0°C per cycle) with anti-oscillation algorithms
- Advanced mode management with offset adjustments and thermal state tracking
- Multi-layer safety constraints with temperature clamping and deviation monitoring
- Adaptive feedback loops with temperature stability detection and response timing optimization

**Reliable & Safe**
- Continues working if sensors fail
- Manual override always available
- Robust training data persistence with configurable save intervals
- Enhanced shutdown save with timeout protection
- Save diagnostics and monitoring in Home Assistant UI
- Backward-compatible persistence schema
- Comprehensive debug logging for troubleshooting

## Quick Start

### Installation

**Option 1: HACS (Recommended)**
1. Add this repository to HACS custom repositories
2. Install "Smart Climate Control"
3. Restart Home Assistant

**Option 2: Manual**
1. Copy `custom_components/smart_climate` to your `custom_components` folder
2. Restart Home Assistant

### Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Smart Climate Control"
3. Select your climate entity and room temperature sensor
4. Optionally add outdoor temperature and power sensors
5. Configure all your preferences through the intuitive UI:
   - Temperature limits and offset settings
   - Mode-specific temperatures and offsets
   - Learning system parameters and confidence thresholds
   - Power thresholds for AC detection and hysteresis learning
   - Update intervals and adaptive adjustment rates
   - Weather integration settings for predictive strategies
   - Seasonal adaptation parameters and outdoor temperature buckets
   - Default target temperature (16-30°C)

That's it! Your new smart climate entity is ready to use. No YAML editing required!

### Basic Usage

- Set your desired temperature normally - the intelligent algorithms handle optimization automatically
- Enable learning to activate multi-layered ML: hysteresis detection, seasonal adaptation, and predictive strategies
- The system automatically learns AC response timing and adjusts feedback delays for optimal efficiency
- Weather-aware predictive adjustments activate automatically based on forecast patterns
- Seasonal learning adapts to outdoor temperature changes without manual intervention
- Monitor real-time learning metrics, confidence levels, and prediction accuracy through rich entity attributes
- Use preset modes for different thermal scenarios with mode-specific offset adjustments

### Dashboard Setup (NEW!)

1. After installation, dashboard sensors are created automatically
2. Go to Developer Tools → Services
3. Search for "Smart Climate: Generate Dashboard"
4. Select your Smart Climate entity and click "Call Service"
5. A notification appears with your custom dashboard YAML
6. Follow the instructions in the notification to create your dashboard

## Documentation

**Setup & Configuration**
- [Installation Guide](docs/installation.md) - Detailed installation instructions
- [Configuration Guide](docs/configuration.md) - All configuration options explained
- [Sensor Setup](docs/sensors.md) - Sensor requirements and best practices

**Usage & Features**
- [Usage Guide](docs/usage.md) - How to use all features effectively
- [Dashboard Setup](docs/dashboard-setup.md) - **NEW!** Visualization dashboard blueprint
- [Learning System](docs/learning-system.md) - Understanding the intelligent learning
- [Troubleshooting](docs/troubleshooting.md) - Solving common issues

**Technical & Development**
- [Architecture Overview](docs/architecture.md) - Technical design documentation
- [Contributing Guide](docs/contributing.md) - How to contribute to the project

## Example Configuration

The UI configuration now handles all settings, making YAML configuration optional:

```yaml
# YAML configuration is optional - UI configuration is recommended
# All settings below can be configured through the UI
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    power_sensor: sensor.ac_power  # Optional: enables HysteresisLearner
    default_target_temperature: 24  # Optional: your preferred default (16-30°C)
```

## Requirements

- Home Assistant 2024.1 or newer
- Python 3.11 or newer
- A climate entity (AC, heat pump, etc.)
- A temperature sensor in the same room

## Support

- **Issues**: [GitHub Issues](https://github.com/VectorBarks/smart-climate/issues)
- **Discussions**: [GitHub Discussions](https://github.com/VectorBarks/smart-climate/discussions)
- **Documentation**: [Full Documentation](docs/)

## Project Status

**Version 1.3.0 Released**: Advanced predictive intelligence with multi-layered learning algorithms!

**New in v1.3.0:**
- **Adaptive Feedback Delays**: ML-powered AC response timing optimization with exponential smoothing
- **Weather Forecast Integration**: Proactive temperature strategies using heat wave detection and thermal optimization
- **Seasonal Adaptation**: Context-aware hysteresis learning with outdoor temperature pattern correlation
- **Enhanced Learning Architecture**: Multi-factor confidence calculation with logarithmic scaling
- **Predictive Algorithms**: Weather-aware offset calculation and seasonal pattern bucket matching
- **Advanced Telemetry**: Real-time learning metrics with <1ms prediction latency monitoring

**Previous v1.0.x improvements:**
- Fixed learning data collection with feedback mechanism
- Corrected offset calculations for proper cooling/heating
- Complete UI configuration for all settings
- Reorganized documentation for better accessibility

This is a personal project developed for educational purposes and community use. While functional and tested, it comes with no warranties. Always test thoroughly in your environment.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Home Assistant team for the excellent platform
- The HACS community for making distribution easy
- All contributors and testers who help improve this integration

---

**Made with love for the Home Assistant community**
