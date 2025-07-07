# Smart Climate Control for Home Assistant

> Transform any climate device with inaccurate sensors into an intelligent, self-learning climate control system.

[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)

## Overview

Smart Climate Control is a Home Assistant custom integration that creates a virtual climate entity to compensate for temperature sensor inaccuracies in any climate control device. Using a hybrid approach of immediate rule-based control with **lightweight learning intelligence**, it maintains your desired room temperature based on external trusted sensors.

**🎉 Phase 2A Complete**: Now includes intelligent pattern learning, UI controls, and persistent learning across Home Assistant restarts!

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
- **Intelligent learning** - Learns time-of-day patterns and environmental effects
- **Energy efficiency** - Reduces unnecessary cycling and energy waste  
- **User-friendly controls** - Easy learning toggle and rich status information
- **Universal compatibility** - Works with any Home Assistant climate entity

## Features

### **Universal Compatibility**
- Works with **ANY** Home Assistant climate entity (WiFi, Zigbee, Z-Wave, IR, etc.)
- Compatible with **ANY** temperature sensor platform
- No device-specific dependencies or limitations

### **Intelligent Offset Compensation**
- **Lightweight learning**: Incremental pattern learning with <1ms predictions
- **Hybrid approach**: Immediate rule-based control + adaptive learning
- **Dynamic calculations**: Offsets adapt to time-of-day and environmental conditions
- **Power awareness**: Optional power monitoring for enhanced accuracy
- **Safety limits**: Configurable temperature and offset limits prevent extremes
- **Gradual adjustments**: Smooth transitions prevent temperature oscillation (0.5°C per 3-minute cycle)

### **Operating Modes**
- **Normal**: Standard operation with dynamic offset compensation
- **Away**: Fixed energy-saving temperature (default 26°C, configurable)
- **Sleep**: Reduced cooling for quieter nighttime operation  
- **Boost**: Extra cooling for rapid temperature reduction

### **Flexible Configuration**
- **UI Setup**: Easy configuration through Home Assistant interface
- **Learning Controls**: Simple switch entity to enable/disable learning with progress monitoring
- **YAML Support**: Advanced configuration for power users
- **Entity Selectors**: Choose your climate device and sensors from dropdowns
- **Optional Sensors**: Outdoor temperature and power monitoring for enhanced accuracy

### **Safety & Control**
- **Manual Overrides**: Temporary offset adjustments with duration timers
- **Learning Toggle**: Easy on/off control with status monitoring
- **Safety Limits**: Configurable min/max temperatures (default 16-30°C)
- **Offset Limits**: Maximum offset protection (default ±5°C)
- **Graceful Fallbacks**: Continues operation if sensors become unavailable
- **Data Persistence**: Learning patterns survive Home Assistant restarts

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
    
    # Learning settings  
    enable_learning: false  # Learning disabled by default (use UI switch to enable)
    data_retention_days: 60 # Days of data to keep for patterns
    learning_feedback_delay: 45  # Seconds to wait before collecting feedback (default: 45)
```

## Usage

### Basic Operation

Once configured, the Smart Climate Control entity appears in Home Assistant as a standard climate entity with enhanced intelligence:

1. **Set Temperature**: Use the normal climate controls - the system automatically applies offset compensation
2. **Enable Learning**: Use the "{Climate Name} Learning" switch to turn on intelligent pattern learning
3. **Monitor Progress**: Watch learning statistics in the switch entity attributes (samples collected, accuracy, confidence)
4. **Check Logs**: Enable debug logging to see detailed offset calculations and learning progress

### Operating Modes

Switch between modes using the preset selector:

- **None (Normal)**: Dynamic offset compensation based on current conditions
- **Away**: Fixed temperature for energy savings while away from home
- **Sleep**: Quieter operation with reduced cooling demand for nighttime
- **Boost**: Temporary extra cooling for rapid temperature reduction

### Learning Controls

The integration creates a learning switch entity for easy control:

- **Learning Switch**: Turn learning on/off with a simple toggle
- **Learning Statistics**: View samples collected, accuracy, and confidence in entity attributes
- **Persistent Learning**: Patterns are automatically saved and restored across Home Assistant restarts

### Manual Overrides

Use the companion number entities for temporary manual control:

- **Manual Offset** (-5 to +5°C): Override the calculated offset
- **Override Duration** (0-480 minutes): How long the manual override lasts

## How the Learning System Works

### Overview

The learning system uses a feedback mechanism to continuously improve offset predictions by measuring how well each prediction performs in practice. This creates a self-improving system that adapts to your specific AC unit and environment.

### The Feedback Loop

When you adjust the temperature, here's what happens:

1. **Offset Calculation** (T=0 seconds):
   - System calculates an offset based on current conditions
   - Example: You want 22°C, system predicts +2°C offset needed
   - Sends 20°C to the AC unit to compensate for its sensor inaccuracy

2. **Feedback Collection** (T=45 seconds default):
   - Measures the AC's internal sensor temperature
   - Measures the room sensor temperature
   - Calculates the actual offset that exists between them
   - Records this data to improve future predictions

3. **Learning Process**:
   - Compares predicted offset vs actual offset
   - Uses the error to refine future predictions
   - Builds patterns based on time of day, temperatures, and power usage

### What the Feedback Measures

**Important**: The feedback mechanism is NOT waiting for the room to reach target temperature. Instead, it's measuring:

- **Sensor Drift**: How the AC's internal sensor reading differs from the room sensor
- **AC Response**: How the AC unit's sensor responds to setpoint changes
- **Environmental Patterns**: How conditions affect the sensor offset

This typically stabilizes within 30-90 seconds after a setpoint change, which is why the default delay is 45 seconds.

### Configuring the Feedback Delay

The feedback delay is configurable based on your AC unit's characteristics:

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    learning_feedback_delay: 90  # Increase to 90 seconds for slower AC units
```

#### Choosing the Right Delay

- **Fast-responding units** (mini-splits, modern inverters): 30-60 seconds
- **Standard units**: 45-90 seconds (default: 45)
- **Slow-responding units** (older systems, large spaces): 90-180 seconds

To determine the optimal delay for your system:
1. Enable debug logging
2. Watch how long it takes for the AC's internal temperature to stabilize after changes
3. Set the feedback delay slightly longer than this stabilization time

### Learning Data Quality

The learning system includes several mechanisms to ensure data quality:

- **Offset Threshold**: Only collects feedback when an offset was actually applied
- **Sensor Validation**: Skips collection if sensors are unavailable
- **Edge Case Handling**: Properly handles entity removal and Home Assistant restarts
- **Outlier Detection**: Future versions will filter anomalous readings

### Monitoring Learning Progress

Track the learning system's performance through:

1. **Debug Logs**: Show each feedback collection and learning update
   ```
   Learning feedback collected: predicted_offset=2.00°C, actual_offset=2.30°C
   ```

2. **Switch Attributes**: Display real-time statistics
   - `samples_collected`: Total learning samples
   - `accuracy`: Prediction accuracy percentage
   - `confidence`: System confidence level
   - `mean_error`: Average prediction error

3. **Gradual Improvement**: Expect to see accuracy improve over several days as patterns emerge

### Learning System Limitations

Current limitations to be aware of:

- **Single Sample**: Currently takes one measurement per adjustment (future versions may use multiple samples)
- **Fixed Delay**: Uses a fixed delay rather than detecting stability (enhancement planned)
- **Linear Learning**: Uses exponential smoothing rather than complex ML models (by design for efficiency)

### Future Enhancements

Planned improvements for the learning system:

- **Adaptive Delays**: Automatically adjust feedback timing based on AC behavior
- **Multi-point Sampling**: Take multiple measurements to improve accuracy
- **Stability Detection**: Wait for temperature stability rather than fixed time
- **Power-based Learning**: Use power consumption patterns to enhance predictions
- **Seasonal Adaptation**: Adjust learning rates based on seasonal changes

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

### Lightweight Learning Intelligence

The system uses intelligent pattern learning to improve offset predictions over time:

- **Incremental Learning**: Learns patterns one data point at a time without heavy processing
- **Time-of-Day Patterns**: Adapts to daily temperature variation patterns
- **Environmental Correlation**: Learns how outdoor temperature affects offset accuracy
- **Performance Optimized**: <1ms prediction time, <1MB memory usage
- **Confidence Scoring**: Provides transparency into prediction reliability
- **Automatic Persistence**: Learning data automatically saved and restored
- **Fallback Protection**: Rule-based control ensures functionality during learning

### Power Monitoring

If you have a power sensor monitoring your climate device:

- **Enhanced Learning**: Power state data improves pattern learning accuracy
- **State Detection**: Confirms when the device is actively cooling vs. idle
- **Better Predictions**: Learning system understands AC operation cycles
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

**Problem**: Learning predictions seem poor
- **Solution**: Allow more time for data collection (20+ samples minimum, 48-72 hours typical)
- **Check**: Monitor learning statistics in switch entity attributes
- **Option**: Disable learning temporarily using the switch and rely on rule-based calculations

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
- Learning data collection and pattern updates
- Sensor readings and state changes
- Mode switches and manual overrides
- Learning system predictions and confidence levels
- Data persistence operations

## Architecture

The integration follows a modular design with clearly separated concerns:

- **SmartClimateEntity**: Main climate entity that users interact with
- **OffsetEngine**: Calculates temperature offsets using rules and lightweight learning
- **LightweightOffsetLearner**: Incremental pattern learning with exponential smoothing
- **SensorManager**: Handles all sensor reading and state monitoring
- **ModeManager**: Manages operating modes and their specific behaviors
- **TemperatureController**: Applies offsets and enforces safety limits
- **DataStore**: Atomic JSON persistence with backup safety
- **Switch Platform**: UI controls for learning enable/disable

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

### Phase 2A: Lightweight Learning ✅ Complete
- [x] Incremental pattern learning system
- [x] UI switch controls for learning
- [x] Data persistence across restarts
- [x] Debug logging and troubleshooting

### Phase 2B: Enhanced Learning Features
- [ ] Power pattern analysis and AC operation detection
- [ ] Mode-specific learning models
- [ ] Weather forecast integration
- [ ] Seasonal pattern recognition

### Phase 3: Visualization & Analytics
- [ ] Custom Lovelace cards for monitoring
- [ ] Offset history graphs and trends
- [ ] Learning progress indicators
- [ ] Energy usage analytics

### Phase 4: Advanced Features  
- [ ] Multi-zone coordination
- [ ] Occupancy-based automation
- [ ] Integration with utility time-of-use rates
- [ ] Predictive pre-cooling/heating

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