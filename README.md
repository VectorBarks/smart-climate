# Smart Climate Control for Home Assistant

> Transform any climate device with inaccurate sensors into an intelligent, self-learning climate control system.

[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

## Overview

Smart Climate Control is a Home Assistant custom integration that creates a virtual climate entity to compensate for temperature sensor inaccuracies in any climate control device. Using a hybrid approach of immediate rule-based control with background machine learning, it maintains your desired room temperature based on external trusted sensors.

## Important Notice

This is a personal pet project developed for educational and personal use. While the integration has been tested and is functional, no guarantees are provided regarding reliability, compatibility, or fitness for any particular purpose. Use at your own discretion and always test thoroughly in your environment before relying on this integration for critical climate control.

### The Problem
Many climate control devices (AC units, heat pumps, mini-splits) suffer from inaccurate internal temperature sensors with offsets that vary based on:
- Outdoor temperature conditions
- Time of day and seasonal changes  
- Heat sources from neighboring units or appliances
- Device placement and airflow patterns

Simple fixed offset corrections are inadequate for these dynamic conditions.

### The Solution
Smart Climate Control dynamically calculates and applies temperature offsets in real-time, learning from your environment to provide:
- **Accurate climate control** - Maintains your desired temperature within ±0.5°C
- **Energy efficiency** - Reduces unnecessary cycling and energy waste
- **Adaptive learning** - Improves performance over time
- **Universal compatibility** - Works with any Home Assistant climate entity

## Features

### **Universal Compatibility**
- Works with **ANY** Home Assistant climate entity (WiFi, Zigbee, Z-Wave, IR, etc.)
- Compatible with **ANY** temperature sensor platform
- No device-specific dependencies or limitations

### **Intelligent Offset Compensation**
- **Hybrid approach**: Immediate rule-based control + background ML learning
- **Dynamic calculations**: Offsets adapt to environmental conditions
- **Safety limits**: Configurable temperature and offset limits prevent extremes
- **Gradual adjustments**: Smooth transitions prevent temperature oscillation

### **Operating Modes**
- **Normal**: Standard operation with dynamic offset compensation
- **Away**: Fixed energy-saving temperature (default 26°C, configurable)
- **Sleep**: Reduced cooling for quieter nighttime operation  
- **Boost**: Extra cooling for rapid temperature reduction

### **Flexible Configuration**
- **UI Setup**: Easy configuration through Home Assistant interface
- **YAML Support**: Advanced configuration for power users
- **Entity Selectors**: Choose your climate device and sensors from dropdowns
- **Optional Sensors**: Outdoor temperature and power monitoring for enhanced accuracy

### **Safety & Control**
- **Manual Overrides**: Temporary offset adjustments with duration timers
- **Safety Limits**: Configurable min/max temperatures (default 16-30°C)
- **Offset Limits**: Maximum offset protection (default ±5°C)
- **Graceful Fallbacks**: Continues operation if sensors become unavailable

## Installation

### Option 1: HACS (Recommended)

1. **Add Repository**: 
   - Open HACS in Home Assistant
   - Go to "Integrations" 
   - Click the three dots menu → "Custom repositories"
   - Add this repository URL and select "Integration"

2. **Install**:
   - Search for "Smart Climate Control"
   - Click "Install"
   - Restart Home Assistant

3. **Configure**:
   - Go to Settings → Devices & Services
   - Click "Add Integration" 
   - Search for "Smart Climate Control"

### Option 2: Manual Installation

1. **Download**: Copy the `custom_components/smart_climate` folder to your Home Assistant `custom_components` directory

2. **Restart**: Restart Home Assistant

3. **Configure**: Follow step 3 from the HACS installation above

## Configuration

### UI Configuration (Recommended)

The integration provides an intuitive setup wizard:

1. **Climate Entity**: Select your existing climate device
2. **Room Sensor**: Choose a trusted temperature sensor for the room
3. **Optional Sensors**:
   - **Outdoor Sensor**: For better offset predictions
   - **Power Sensor**: For improved state detection
4. **Settings**: Configure temperature limits, update intervals, and mode defaults

### YAML Configuration

For advanced users, YAML configuration is supported:

```yaml
# configuration.yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    outdoor_sensor: sensor.outdoor_temperature  # optional
    power_sensor: sensor.ac_power_consumption   # optional
    
    # Optional settings with defaults
    min_temperature: 16      # Minimum temperature limit
    max_temperature: 30      # Maximum temperature limit  
    max_offset: 5           # Maximum offset allowed
    update_interval: 180    # Update frequency in seconds
    
    # Mode settings
    away_temperature: 26    # Fixed temperature for away mode
    sleep_offset: 1.0       # Extra offset for sleep mode
    boost_offset: -2.0      # Extra cooling for boost mode
    
    # ML settings  
    ml_enabled: true        # Enable machine learning
    data_retention_days: 60 # Days of data to keep for training
```

## Usage

### Basic Operation

Once configured, the Smart Climate Control entity appears in Home Assistant as a standard climate entity with enhanced intelligence:

1. **Set Temperature**: Use the normal climate controls - the system automatically applies offset compensation
2. **Monitor Performance**: Watch as the system learns your environment and improves accuracy over time
3. **Check Logs**: Review detailed logs showing offset calculations and system decisions

### Operating Modes

Switch between modes using the preset selector:

- **None (Normal)**: Dynamic offset compensation based on current conditions
- **Away**: Fixed temperature for energy savings while away from home
- **Sleep**: Quieter operation with reduced cooling demand for nighttime
- **Boost**: Temporary extra cooling for rapid temperature reduction

### Manual Overrides

Use the companion number entities for temporary manual control:

- **Manual Offset** (-5 to +5°C): Override the calculated offset
- **Override Duration** (0-480 minutes): How long the manual override lasts

## Sensor Availability & Behavior

Smart Climate Control handles sensor availability gracefully to ensure reliable operation:

### Critical Sensors

**Room Temperature Sensor** (Required)
- **When Available**: Provides current room temperature for accurate offset calculations
- **When Unavailable**: The Smart Climate entity shows no current temperature (`current_temperature` becomes `None`)
- **Impact**: The system cannot calculate accurate offsets without room temperature data
- **Recovery**: Automatically resumes normal operation when the sensor becomes available again

### Optional Sensors

**Thermostat/Climate Device** (Wrapped Entity)
- **When Available**: Full climate control functionality with temperature setpoints and mode changes
- **When Unavailable**: The Smart Climate entity can still show room temperature from the sensor, but cannot control the actual device
- **Impact**: Temperature control commands will not be executed until the device becomes available
- **Recovery**: Control commands are queued and executed when the device reconnects

**Outdoor Temperature Sensor** (Optional)
- **When Available**: Enhances offset calculations with outdoor temperature correlation
- **When Unavailable**: System continues normal operation using only room temperature data
- **Impact**: Slightly reduced accuracy for outdoor temperature-dependent offset patterns
- **Recovery**: Seamlessly incorporates outdoor data when the sensor becomes available

**Power Consumption Sensor** (Optional)
- **When Available**: Provides better detection of actual cooling/heating operation
- **When Unavailable**: System relies on HVAC mode and state for operation detection
- **Impact**: Minimal impact on core functionality
- **Recovery**: Enhanced state detection resumes when power sensor becomes available

### Sensor Reliability Features

- **Graceful Degradation**: The system continues operating with available sensors
- **Automatic Recovery**: Full functionality resumes when sensors become available
- **Fallback Defaults**: Sensible defaults prevent system failures
- **Status Logging**: Sensor availability changes are logged for troubleshooting
- **No Manual Intervention**: Recovery is automatic without requiring restarts

### Important Notes

- The **room temperature sensor is critical** - without it, the system cannot calculate meaningful offsets
- All other sensors are optional and the system adapts to their availability
- Sensor unavailability is temporary in most cases (network issues, device restarts, etc.)
- The system is designed to be resilient and continue operating during sensor outages

## Advanced Features

### Machine Learning

The system continuously learns from your environment to improve offset predictions:

- **Training Data**: Collects temperature readings, weather conditions, and system performance
- **Online Learning**: Updates predictions without requiring restarts
- **Confidence Scoring**: Provides transparency into prediction reliability
- **Fallback Protection**: Rule-based control ensures functionality during ML training

### Power Monitoring

If you have a power sensor monitoring your climate device:

- **State Detection**: Confirms when the device is actively cooling vs. idle
- **Improved Accuracy**: Better offset calculations based on actual operation
- **Energy Insights**: Understanding of power consumption patterns

### Data Privacy

All data processing occurs locally on your Home Assistant instance:
- No cloud services or external data transmission
- Historical data stored in local SQLite database
- Configurable data retention periods

## Troubleshooting

### Common Issues

**Problem**: Offset seems incorrect
- **Solution**: Check that your room sensor is properly positioned and calibrated
- **Tip**: Use the manual override to test different offset values

**Problem**: System not responding to temperature changes
- **Solution**: Verify the climate entity and room sensor are working correctly
- **Check**: Review logs for error messages or sensor communication issues

**Problem**: ML predictions seem poor
- **Solution**: Allow more time for data collection (48-72 hours minimum)
- **Option**: Disable ML temporarily and rely on rule-based calculations

### Logs and Debugging

Enable debug logging to see detailed system operation:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.smart_climate: debug
```

This will show:
- Offset calculations and reasoning
- Sensor readings and state changes
- Mode switches and manual overrides
- ML model predictions and confidence levels

## Architecture

The integration follows a modular design with clearly separated concerns:

- **SmartClimateEntity**: Main climate entity that users interact with
- **OffsetEngine**: Calculates temperature offsets using rules and ML
- **SensorManager**: Handles all sensor reading and state monitoring
- **ModeManager**: Manages operating modes and their specific behaviors
- **TemperatureController**: Applies offsets and enforces safety limits

This architecture ensures:
- **Reliability**: Component failures don't crash the entire system
- **Testability**: Each component can be thoroughly tested in isolation
- **Maintainability**: Clear separation makes debugging and enhancement easier
- **Extensibility**: New features can be added without affecting existing functionality

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:
- Code standards and testing requirements
- How to set up a development environment
- Submitting bug reports and feature requests
- Creating pull requests

## Roadmap

### Phase 2: Enhanced ML Features
- [ ] Mode-specific learning models
- [ ] Weather forecast integration
- [ ] Seasonal pattern recognition
- [ ] Multi-zone coordination

### Phase 3: Visualization & Analytics
- [ ] Custom Lovelace cards for monitoring
- [ ] Offset history graphs and trends
- [ ] Learning progress indicators
- [ ] Energy usage analytics

### Phase 4: Advanced Features  
- [ ] Occupancy-based automation
- [ ] Integration with utility time-of-use rates
- [ ] Predictive pre-cooling/heating
- [ ] Advanced scheduling with machine learning

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/VectorBarks/smart-climate/issues)
- **Discussions**: [GitHub Discussions](https://github.com/VectorBarks/smart-climate/discussions)
- **Home Assistant Community**: [Community Forum Topic](https://community.home-assistant.io/)

## Acknowledgments

- Home Assistant team for the excellent platform and developer tools
- The Home Assistant community for testing and feedback
- Contributors who helped shape this integration

---

**Made for smarter climate control**