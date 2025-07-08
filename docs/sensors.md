# Sensor Documentation

This guide covers sensor requirements, behavior, and best practices for Smart Climate Control.

## Sensor Types and Roles

Smart Climate Control uses different types of sensors to provide intelligent temperature management:

### Room Temperature Sensor (Required)

The room temperature sensor is the most critical component for accurate climate control.

**Purpose**: Provides the actual room temperature for offset calculations

**Requirements**:
- Must provide numeric temperature values
- Should update at least every 5 minutes
- Accuracy of ±0.5°C or better recommended
- Must be a `sensor` entity with temperature device class

**Supported Sensor Types**:
- Zigbee temperature sensors (Aqara, Sonoff, etc.)
- Z-Wave temperature sensors
- WiFi sensors (ESPHome, Tasmota)
- Bluetooth sensors (Xiaomi, SwitchBot)
- Integrated sensors (Ecobee, Nest remote sensors)

### Climate Entity Internal Sensor

Every climate device has an internal temperature sensor that Smart Climate Control reads.

**Purpose**: Provides the baseline for offset calculations

**Characteristics**:
- Often inaccurate due to placement near heat-generating components
- May be affected by direct airflow
- Typically shows different readings than room temperature
- Accessed automatically through the climate entity

### Outdoor Temperature Sensor (Optional)

An outdoor sensor enhances prediction accuracy by correlating indoor offsets with outdoor conditions.

**Purpose**: Improves offset predictions based on outdoor temperature

**Requirements**:
- Should be shaded from direct sunlight
- Updates at least hourly
- Can be a physical sensor or weather service

**Supported Sources**:
- Physical outdoor sensors
- Weather integrations (OpenWeatherMap, Met.no)
- Local weather stations
- Smart home weather devices

### Power Sensor (Optional)

A power sensor helps detect when your AC is actively cooling versus idle.

**Purpose**: Enhances learning accuracy and state detection

**Requirements**:
- Must monitor the climate device's power consumption
- Should report in Watts (W) or kilowatts (kW)
- Update frequency of 10-60 seconds
- Resolution sufficient to distinguish on/off states

**Supported Types**:
- Smart plugs with power monitoring
- Whole-home energy monitors (with CT clamps)
- Built-in power reporting (some smart ACs)
- Dedicated power meters

## Choosing Between Internal and Remote Sensors

Many AC units support switching between their internal sensor and a remote control sensor. This section helps you choose the best option for Smart Climate Control.

### Why Internal Sensors Often Work Better

Counter-intuitively, internal sensors (especially those at exhaust vents) often provide better results with Smart Climate Control than "somewhat accurate" remote sensors.

**Key Advantages of Internal Exhaust Sensors**:

1. **Predictable Offset Patterns**: Exhaust sensors show large, consistent temperature differences
   - During cooling: Reads 10-15°C below room temperature
   - When idle: Gradually approaches room temperature
   - Pattern is highly predictable and learnable

2. **Clear Operating State Detection**: The large temperature swings make it obvious when the AC is running
   - Cooling: Immediate sharp drop in temperature
   - Idle: Steady rise back toward room temperature
   - No ambiguity about operational state

3. **Thermal Dynamics Explained**: Understanding why internal sensors behave this way helps optimize configuration
   - **During Active Cooling**: Internal fan mixes warm room air with cold evaporator, sensor reads averaged temperature
   - **After Cooling Stops**: No airflow mixing, sensor reads pure evaporator coil temperature (much colder)
   - **Example**: AC target 20.8°C shows 20.8°C while running, drops to 16°C when stopped
   - **Why This Happens**: Evaporator coil stays very cold after compressor stops, gradually warms to room temperature

4. **Better Learning Potential**: Larger offsets provide clearer signals for the learning system
   - More data points across a wider range
   - Clearer correlation patterns
   - Faster convergence to optimal offsets

5. **Perfect for HysteresisLearner**: The new AC temperature window detection feature thrives on these patterns
   - **Clear Transitions**: 4-5°C difference between cooling/idle makes state detection trivial
   - **Reliable Thresholds**: Consistent temperature drops enable robust learning of start/stop points
   - **Enhanced Predictions**: System quickly learns your AC's cooling cycle behavior

6. **Avoids Double Correction**: Remote sensors with small offsets risk overcorrection
   - If remote sensor reads 23°C and room is 24°C (1°C difference)
   - Smart Climate might add another 1-2°C offset
   - Result: AC set to 21°C when 22°C would suffice

### When to Use Internal Sensors

**Recommended When**:
- Internal sensor is at the exhaust vent (reads very cold during cooling)
- You want the most accurate learning over time
- The offset is large but consistent
- You have good room temperature sensor placement

**Example Configuration**:
```yaml
# AC unit set to use internal sensor mode
climate:
  - platform: your_ac_platform
    name: "Living Room AC"
    sensor_mode: "internal"  # Platform-specific setting

smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    enable_learning: true  # Works great with predictable offsets
```

### When to Consider Remote Sensors

**Consider When**:
- Remote sensor is significantly more accurate than internal
- Internal sensor has erratic, unpredictable behavior
- Remote sensor is in a better location than your room sensor
- You don't plan to use the learning features

**Caution**: If the remote sensor is "somewhat accurate" (within 1-2°C of actual), you may experience:
- Overcorrection issues
- Slower learning convergence
- Less effective offset compensation

### Real-World Example

**Scenario**: AC with switchable internal/remote sensors
- Internal sensor (at exhaust): Shows 8°C when cooling, 22°C when idle
- Remote sensor: Shows 23°C consistently (1°C below actual room temp)
- Actual room temperature: 24°C

**With Internal Sensor**:
- Clear offset pattern: -16°C when cooling, -2°C when idle
- Smart Climate learns these patterns quickly
- Accurate compensation after a few days

**With Remote Sensor**:
- Small offset: -1°C consistently
- Risk of double correction
- Less data for learning system
- May oscillate around setpoint

### Configuration Tips for Exhaust Sensors

When using internal exhaust sensors, optimize your configuration:

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    max_offset: 15  # Allow larger offsets for exhaust sensors
    enable_learning: true
    learning_rate: 0.3  # Faster learning for consistent patterns
```

**Key Settings**:
- **Higher max_offset**: Exhaust sensors need larger offset ranges (10-20°C)
- **Enable learning**: Predictable patterns make learning highly effective
- **Moderate learning_rate**: 0.2-0.4 works well for consistent patterns

### Making the Decision

**Questions to Ask**:
1. How large is the temperature difference between sensors?
   - Large (>5°C) → Use internal sensor
   - Small (<2°C) → Consider remote sensor carefully

2. How consistent is the offset pattern?
   - Very consistent → Use internal sensor
   - Erratic → Try remote sensor

3. Do you want optimal learning performance?
   - Yes → Use internal sensor with large offsets
   - No → Either option works

4. Is the remote sensor truly more accurate?
   - Yes (±0.5°C) → Consider remote sensor
   - Somewhat (±1-2°C) → Stick with internal

### Summary

While it may seem logical to use a "more accurate" remote sensor, Smart Climate Control often performs better with predictable, large-offset internal sensors. The learning system thrives on clear patterns, and exhaust vent sensors provide exactly that. Only switch to remote sensors when they offer significant accuracy improvements without the risk of double correction.

## Sensor Availability and Behavior

### Critical Sensor: Room Temperature

The room temperature sensor is essential for operation:

**When Available**:
- Normal operation with accurate offset calculations
- Current temperature displayed in UI
- Learning system collects data
- All features fully functional

**When Unavailable**:
- Smart Climate entity shows no current temperature
- Offset calculations suspended
- No new learning data collected
- Commands still sent but without compensation

**Recovery**: Automatic when sensor returns online

### Wrapped Climate Entity

The underlying climate device must be available for control:

**When Available**:
- Full climate control functionality
- Temperature commands executed
- Mode changes applied
- Internal sensor readings accessed

**When Unavailable**:
- Room temperature still displayed (if sensor available)
- No control commands possible
- Offset calculations continue but not applied
- System waits for device return

**Recovery**: Queued commands execute when device returns

### Optional Sensors

Optional sensors enhance functionality but aren't required:

**Outdoor Temperature**:
- When available: Enhanced offset predictions
- When unavailable: Uses time-based patterns only
- Impact: 10-15% accuracy improvement when available

**Power Sensor**:
- When available: Better cooling/idle detection
- When unavailable: Relies on temperature changes
- Impact: Faster learning, better state detection

## Sensor Placement Best Practices

### Room Temperature Sensor Placement

**Optimal Placement**:
- Mount at 1.2-1.5m (4-5 feet) height
- On interior wall away from exterior walls
- Away from direct sunlight or windows
- Not above heat sources (TVs, lamps, electronics)
- Clear of furniture that blocks airflow
- Not in direct AC airflow path

**Avoid Placing Near**:
- Air conditioning vents
- Doorways with drafts
- Kitchen appliances
- Bathrooms with humidity
- Electronic equipment
- Exterior walls

**Multiple Sensors**: If using multiple sensors, place the primary one where you spend most time (sofa, bed, desk area).

### Outdoor Sensor Placement

**Optimal Placement**:
- North-facing location (Northern Hemisphere)
- Under eave or dedicated shelter
- Good air circulation
- 1.5-2m above ground
- Away from concrete/asphalt
- Protected from rain

**Avoid**:
- Direct sunlight
- Above hot surfaces
- Near AC condensers
- Close to windows/doors
- Areas with poor ventilation

## Sensor Configuration

### Basic Configuration

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    outdoor_sensor: sensor.outdoor_temperature  # optional
    power_sensor: sensor.ac_power              # optional
```

### Multiple Room Sensors

While Smart Climate uses a single primary sensor, you can create template sensors to average multiple readings:

```yaml
template:
  - sensor:
      - name: "Living Room Average Temperature"
        unit_of_measurement: "°C"
        device_class: temperature
        state: >
          {% set sensors = [
            states('sensor.living_room_temp_1'),
            states('sensor.living_room_temp_2'),
            states('sensor.living_room_temp_3')
          ] | select('is_number') | map('float') | list %}
          {{ (sensors | sum / sensors | length) | round(1) if sensors else 'unavailable' }}
```

### Sensor Filtering

For noisy sensors, create a filtered sensor:

```yaml
sensor:
  - platform: filter
    name: "Filtered Room Temperature"
    entity_id: sensor.raw_room_temperature
    filters:
      - filter: outlier
        window_size: 3
        radius: 1.0
      - filter: time_simple_moving_average
        window_size: "00:02:00"
```

## Sensor Accuracy and Calibration

### Checking Sensor Accuracy

1. **Compare Multiple Sensors**: Place 2-3 sensors together temporarily
2. **Use a Reference**: Compare with a known accurate thermometer
3. **Check Consistency**: Ensure stable readings without wild fluctuations
4. **Monitor Trends**: Look for gradual drift over time

### Calibrating Sensors

Many sensors support calibration offsets:

**ESPHome Sensors**:
```yaml
sensor:
  - platform: dht
    temperature:
      name: "Room Temperature"
      filters:
        - offset: -0.5  # Calibration offset
```

**Zigbee Sensors** (via Zigbee2MQTT):
```yaml
devices:
  '0x00158d0001234567':
    temperature_calibration: -0.5
```

**Template Calibration**:
```yaml
template:
  - sensor:
      - name: "Calibrated Room Temperature"
        unit_of_measurement: "°C"
        device_class: temperature
        state: "{{ (states('sensor.room_temp') | float - 0.5) | round(1) }}"
```

## Power Sensor Integration

### Power Consumption Patterns

Understanding your AC's power patterns helps configure the system:

**Typical Patterns**:
- **Idle**: 50-200W (control circuits only)
- **Fan Only**: 100-300W
- **Cooling**: 500-3000W (depends on size)
- **Startup Spike**: 2-5x running power (brief)

### Configuring Power Thresholds

Smart Climate Control now supports configurable power thresholds to better detect AC operating states:

**Power Thresholds** (configurable in UI when power sensor is present):
- **Power Idle Threshold**: Power consumption below this indicates AC is idle or off
- **Power Min Threshold**: Power consumption below this indicates AC running at minimum
- **Power Max Threshold**: Power consumption above this indicates AC running at high/max

**Default Values**:
- Idle: 50W (typical standby power)
- Min: 100W (low fan operation)
- Max: 250W (active cooling threshold)

### How Power Thresholds Work

The system uses these thresholds to determine AC state:

1. **Power < Idle Threshold (50W)**: AC is off or in standby
   - No active cooling happening
   - Learning system notes this as "idle" state
   
2. **Idle < Power < Min Threshold (50-100W)**: AC is on but minimal operation
   - Usually just fan running
   - Minimal cooling effect
   
3. **Min < Power < Max Threshold (100-250W)**: AC is cooling moderately
   - Normal operation range
   - Active temperature control
   
4. **Power > Max Threshold (>250W)**: AC is working hard
   - Maximum cooling mode
   - Usually during initial cooldown or extreme heat

### Adjusting Thresholds for Your AC

Different AC units have different power consumption patterns. Here's how to determine the right thresholds:

**Small Window/Portable Units (5,000-8,000 BTU)**:
```yaml
power_idle_threshold: 30    # Lower standby power
power_min_threshold: 80     # Smaller compressor
power_max_threshold: 600    # Max around 600-800W
```

**Medium Split Systems (12,000-18,000 BTU)**:
```yaml
power_idle_threshold: 50    # Default values work well
power_min_threshold: 100    
power_max_threshold: 1200   # Higher max power
```

**Large Central AC (24,000+ BTU)**:
```yaml
power_idle_threshold: 100   # Control circuits use more
power_min_threshold: 300    # Larger fans
power_max_threshold: 3000   # Much higher cooling power
```

### Determining Your AC's Thresholds

1. **Enable debug logging** to see power readings:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.smart_climate: debug
   ```

2. **Monitor power consumption** in different states:
   - AC completely off
   - AC on but not cooling (fan only)
   - AC cooling normally
   - AC cooling at maximum (hot day)

3. **Set thresholds** based on observations:
   - Idle: Slightly above "off" power reading
   - Min: Between fan-only and light cooling
   - Max: Between normal and maximum cooling

### Example Configuration

**UI Configuration**: When you configure a power sensor, three new fields appear:
- Power Idle Threshold (W): 10-500W range
- Power Min Threshold (W): 50-1000W range  
- Power Max Threshold (W): 100-5000W range

**YAML Configuration**:
```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    power_sensor: sensor.ac_smart_plug_power
    power_idle_threshold: 45     # My AC uses 40W in standby
    power_min_threshold: 120     # Fan only is about 110W
    power_max_threshold: 850     # Peaks at 900W on hot days
```

### Benefits of Proper Threshold Configuration

**Accurate State Detection**:
- Know exactly when AC is cooling vs idle
- Better learning data quality
- More accurate offset predictions

**Energy Awareness**:
- Track actual cooling periods
- Identify efficiency issues
- Monitor power consumption patterns

**Enhanced Learning**:
- Correlate power states with temperature changes
- Learn different offset patterns for different power levels
- Adapt to AC behavior over time

## Troubleshooting Sensor Issues

### Common Problems and Solutions

**Sensor Shows Unavailable**:
- Check network connectivity (WiFi/Zigbee)
- Verify battery levels
- Check integration status
- Review logs for errors

**Erratic Readings**:
- Check for interference sources
- Verify sensor placement
- Consider filtering (see above)
- Replace batteries if applicable

**Slow Updates**:
- Check sensor polling intervals
- Verify network reliability
- Consider sensor firmware updates
- Review integration settings

**Offset Calculations Seem Wrong**:
- Verify both sensors are accurate
- Check sensor placement
- Ensure sensors update regularly
- Review debug logs

### Debug Logging for Sensors

Enable sensor-specific debugging:

```yaml
logger:
  default: info
  logs:
    custom_components.smart_climate.sensor_manager: debug
```

Monitor sensor readings in logs:
```
DEBUG: Room temperature: 22.5°C (sensor.living_room_temperature)
DEBUG: AC internal temperature: 20.8°C
DEBUG: Outdoor temperature: 28.3°C (sensor.outdoor_temperature)
DEBUG: Power consumption: 1250W (sensor.ac_power)
```

## Advanced Sensor Features

### Sensor Attributes

Smart Climate exposes useful sensor information:

```yaml
climate.living_room_smart_ac:
  room_sensor_available: true
  outdoor_sensor_available: true
  power_sensor_available: false
  last_room_temp_update: "2024-01-15 14:30:15"
  sensor_offset_current: 1.7
```

### Sensor Health Monitoring

Create automations to monitor sensor health:

```yaml
automation:
  - alias: "Alert on Room Sensor Failure"
    trigger:
      - platform: state
        entity_id: sensor.living_room_temperature
        to: 'unavailable'
        for: '00:10:00'
    action:
      - service: notify.mobile_app
        data:
          title: "Sensor Alert"
          message: "Living room temperature sensor is offline"
```

### Using Multiple Climate Zones

For multi-zone setups, each Smart Climate instance uses its own sensors:

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    outdoor_sensor: sensor.outdoor_temperature  # Shared
    
  - name: "Bedroom Smart AC"
    climate_entity: climate.bedroom_ac
    room_sensor: sensor.bedroom_temperature
    outdoor_sensor: sensor.outdoor_temperature  # Shared
```

## Future Sensor Enhancements

### Planned Features

**Multi-Sensor Support**: 
- Average multiple room sensors
- Weighted sensor priorities
- Automatic outlier detection

**Advanced Power Analysis**:
- Power pattern learning
- Efficiency monitoring
- Predictive maintenance alerts

**Sensor Fusion**:
- Combine multiple data sources
- Virtual sensor creation
- Enhanced accuracy algorithms

## Best Practices Summary

1. **Prioritize Room Sensor Quality**: Invest in accurate, responsive sensors
2. **Optimal Placement**: Follow placement guidelines for best results
3. **Regular Calibration**: Check and calibrate sensors periodically
4. **Monitor Availability**: Set up alerts for sensor failures
5. **Use Filtering**: Apply filters for noisy sensors
6. **Consider Redundancy**: Multiple sensors for critical areas

For more information:
- [Configuration Guide](configuration.md) - Sensor setup details
- [Troubleshooting Guide](troubleshooting.md) - Solving sensor issues
- [Architecture Guide](architecture.md) - Technical sensor integration