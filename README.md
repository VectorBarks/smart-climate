# Smart Climate Control for Home Assistant

[![Version](https://img.shields.io/badge/Version-1.1.0-brightgreen.svg)](https://github.com/VectorBarks/smart-climate/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

Transform any climate device with inaccurate sensors into an intelligent, self-learning climate control system.

## The Problem

Many AC units and heat pumps have poorly placed internal temperature sensors that don't reflect actual room temperature. This leads to uncomfortable spaces and wasted energy as the unit can't accurately maintain your desired temperature.

## The Solution

Smart Climate Control creates a virtual climate entity that:
- Uses your accurate room sensor instead of the AC's internal sensor
- Dynamically calculates and applies temperature offsets
- Learns from your specific environment over time
- Maintains your desired comfort level automatically

## Key Features

**NEW in v1.1.0: HysteresisLearner - AC Temperature Window Detection**
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
- Advanced ML learns your AC's behavior patterns over time
- HysteresisLearner detects AC operating windows automatically
- Adapts to time-of-day and seasonal changes
- Optional power monitoring for enhanced learning accuracy
- Learning switch with timestamp tracking (see when learning started)
- Enable/disable learning anytime with a simple switch

**Smart Operation**
- Immediate rule-based control (no waiting for learning)
- Gradual adjustments prevent temperature oscillation
- Multiple operating modes (Normal, Away, Sleep, Boost)
- Safety limits prevent extreme temperatures
- Intelligent feedback system for continuous improvement

**Reliable & Safe**
- Continues working if sensors fail
- Manual override always available
- Persists learning data across restarts
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
   - Learning system parameters
   - Power thresholds for AC detection
   - Update intervals and adjustment rates
   - Default target temperature (16-30°C)

That's it! Your new smart climate entity is ready to use. No YAML editing required!

### Basic Usage

- Set your desired temperature normally - the system handles the rest
- Enable learning with the provided switch entity for improved accuracy over time
- The HysteresisLearner will automatically detect your AC's operating patterns
- Check the learning switch attributes to see timestamps and learning progress
- Use preset modes for different scenarios (Away, Sleep, Boost)
- Monitor performance through entity attributes

## Documentation

**Setup & Configuration**
- [Installation Guide](docs/installation.md) - Detailed installation instructions
- [Configuration Guide](docs/configuration.md) - All configuration options explained
- [Sensor Setup](docs/sensors.md) - Sensor requirements and best practices

**Usage & Features**
- [Usage Guide](docs/usage.md) - How to use all features effectively
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

**Version 1.1.0 Released**: Production-ready with HysteresisLearner and enhanced learning capabilities!

**New in v1.1.0:**
- HysteresisLearner: Automatic AC temperature window detection
- Enhanced learning system with power monitoring integration
- Learning switch with timestamp tracking
- Configurable default target temperature
- Fixed all Home Assistant integration compatibility issues
- Improved feedback system for better learning accuracy
- Backward-compatible persistence schema

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
