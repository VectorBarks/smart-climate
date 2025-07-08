# Smart Climate Control for Home Assistant

[![Version](https://img.shields.io/badge/Version-1.0.1-brightgreen.svg)](https://github.com/VectorBarks/smart-climate/releases)
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

**Universal Compatibility**
- Works with ANY Home Assistant climate entity
- Compatible with ANY temperature sensor
- No device-specific limitations

**Intelligent Learning**
- Lightweight ML learns your AC's behavior patterns
- AC temperature window detection (HysteresisLearner) for enhanced accuracy
- Adapts to time-of-day and seasonal changes
- Optional power monitoring for cycle detection and learning
- Learning can be enabled/disabled with a simple switch

**Smart Operation**
- Immediate rule-based control (no waiting for learning)
- Gradual adjustments prevent temperature oscillation
- Multiple operating modes (Normal, Away, Sleep, Boost)
- Safety limits prevent extreme temperatures

**Reliable & Safe**
- Continues working if sensors fail
- Manual override always available
- Persists learning data across restarts
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
   - Update intervals and adjustment rates

That's it! Your new smart climate entity is ready to use. No YAML editing required!

### Basic Usage

- Set your desired temperature normally - the system handles the rest
- Enable learning with the provided switch entity for improved accuracy over time
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

**Version 1.0.0 Released**: Production-ready with intelligent learning, all critical bugs fixed, and comprehensive documentation.

Recent improvements:
- Fixed learning data collection with feedback mechanism
- Corrected offset calculations for proper cooling/heating
- Reorganized documentation for better accessibility
- Added sensor selection guidance

This is a personal project developed for educational purposes and community use. While functional and tested, it comes with no warranties. Always test thoroughly in your environment.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Home Assistant team for the excellent platform
- The HACS community for making distribution easy
- All contributors and testers who help improve this integration

---

**Made with love for the Home Assistant community**