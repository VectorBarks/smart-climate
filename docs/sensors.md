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

Future versions will support power thresholds:

```yaml
# Future feature example
smart_climate:
  - name: "Living Room Smart AC"
    power_sensor: sensor.ac_power
    power_thresholds:
      idle_below: 200
      cooling_above: 500
```

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