# Configuration Guide

This guide covers all configuration options for Smart Climate Control, including both UI and YAML configuration methods.

## Configuration Methods

Smart Climate Control supports two configuration methods:
- **UI Configuration** (recommended): User-friendly setup through the Home Assistant interface
- **YAML Configuration**: Advanced configuration for power users and automation

## UI Configuration

The UI configuration provides an intuitive setup wizard for most use cases.

### Step 1: Add Integration

1. Navigate to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Smart Climate Control"
4. Click on the integration to start configuration

### Step 2: Basic Configuration

The configuration wizard will guide you through the following settings:

#### Required Settings

**Climate Entity**
- Select your existing climate device from the dropdown
- This is the AC unit, heat pump, or other climate device you want to control
- Examples: `climate.living_room_ac`, `climate.bedroom_minisplit`

**Room Temperature Sensor**
- Choose a trusted temperature sensor in the same room
- This sensor should accurately reflect the room temperature
- Must be a sensor entity that provides numeric temperature values
- Examples: `sensor.living_room_temperature`, `sensor.bedroom_temp`

#### Optional Sensors

**Outdoor Temperature Sensor**
- Select an outdoor temperature sensor if available
- Improves offset predictions based on outdoor conditions
- Can be a weather integration sensor or physical outdoor sensor
- Example: `sensor.outdoor_temperature`, `sensor.weather_temperature`

**Power Consumption Sensor**
- Choose a power sensor monitoring your climate device
- Helps detect when the AC is actively cooling vs idle
- Enhances learning accuracy and state detection
- Example: `sensor.ac_power`, `sensor.smart_plug_power`

### Step 3: Advanced Settings

Click "Show Advanced Options" to configure additional parameters:

**Temperature Limits**
- `Minimum Temperature`: Lowest allowed temperature (default: 16°C)
- `Maximum Temperature`: Highest allowed temperature (default: 30°C)

**Offset Settings**
- `Maximum Offset`: Maximum temperature offset allowed (default: 5°C)
- `Update Interval`: How often to recalculate offsets (default: 180 seconds)

**Mode Configuration**
- `Away Temperature`: Fixed temperature for away mode (default: 26°C)
- `Sleep Mode Offset`: Additional offset for sleep mode (default: 1.0°C)
- `Boost Mode Offset`: Extra cooling for boost mode (default: -2.0°C)

**Learning Settings**
- `Enable Learning`: Start with learning enabled (default: false for safety)
- `Data Retention Days`: Days of historical data to keep (default: 60)
- `Learning Feedback Delay`: Seconds to wait before collecting feedback (default: 45)

### Step 4: Complete Setup

1. Review your configuration
2. Click "Submit" to create the Smart Climate entity
3. The new climate entity will appear in your devices list
4. A learning switch entity will also be created for control

## YAML Configuration

For advanced users who prefer YAML configuration or need to configure multiple devices.

### Basic Configuration

Add to your `configuration.yaml`:

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
```

### Full Configuration Example

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    # Required entities
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    
    # Optional sensors
    outdoor_sensor: sensor.outdoor_temperature
    power_sensor: sensor.ac_power_consumption
    
    # Temperature limits
    min_temperature: 16      # Minimum setpoint temperature
    max_temperature: 30      # Maximum setpoint temperature
    
    # Offset configuration
    max_offset: 5           # Maximum offset in either direction
    update_interval: 180    # Seconds between offset updates
    
    # Mode-specific settings
    away_temperature: 26    # Fixed temp for away mode
    sleep_offset: 1.0       # Extra offset for sleep mode
    boost_offset: -2.0      # Extra cooling for boost mode
    
    # Learning configuration
    enable_learning: false  # Start with learning disabled
    data_retention_days: 60 # Days to keep learning data
    learning_feedback_delay: 45  # Seconds before feedback collection
    
  # You can configure multiple climate devices
  - name: "Bedroom Smart AC"
    climate_entity: climate.bedroom_ac
    room_sensor: sensor.bedroom_temperature
    sleep_offset: 2.0  # Higher offset for bedroom comfort
```

### Configuration Parameters Reference

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | Yes | - | Friendly name for the entity |
| `climate_entity` | entity_id | Yes | - | The climate entity to control |
| `room_sensor` | entity_id | Yes | - | Room temperature sensor |
| `outdoor_sensor` | entity_id | No | None | Outdoor temperature sensor |
| `power_sensor` | entity_id | No | None | Power consumption sensor |
| `min_temperature` | float | No | 16 | Minimum temperature limit (°C) |
| `max_temperature` | float | No | 30 | Maximum temperature limit (°C) |
| `max_offset` | float | No | 5 | Maximum offset allowed (°C) |
| `update_interval` | integer | No | 180 | Update frequency (seconds) |
| `away_temperature` | float | No | 26 | Temperature for away mode (°C) |
| `sleep_offset` | float | No | 1.0 | Additional offset for sleep mode (°C) |
| `boost_offset` | float | No | -2.0 | Additional cooling for boost mode (°C) |
| `enable_learning` | boolean | No | false | Enable learning on startup |
| `data_retention_days` | integer | No | 60 | Days to retain learning data |
| `learning_feedback_delay` | integer | No | 45 | Delay before feedback collection (seconds) |

## Learning Feedback Delay Configuration

The `learning_feedback_delay` parameter controls how long the system waits after a temperature adjustment before measuring the actual sensor offset. This is important for accurate learning.

### Choosing the Right Delay

Different AC units respond at different speeds:

- **Fast-responding units** (modern inverters, mini-splits): 30-60 seconds
- **Standard units**: 45-90 seconds (default: 45)
- **Slow-responding units** (older systems, large spaces): 90-180 seconds

### How to Determine Your Optimal Delay

1. Enable debug logging:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.smart_climate: debug
   ```

2. Make temperature adjustments and observe logs
3. Note how long it takes for the AC's internal temperature to stabilize
4. Set the feedback delay slightly longer than this stabilization time

### Example for Different AC Types

```yaml
smart_climate:
  # Modern mini-split (fast response)
  - name: "Living Room Mini-Split"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temp
    learning_feedback_delay: 30
    
  # Standard central AC (medium response)
  - name: "Main Floor AC"
    climate_entity: climate.central_ac
    room_sensor: sensor.hallway_temp
    learning_feedback_delay: 60
    
  # Older window unit (slow response)
  - name: "Bedroom Window AC"
    climate_entity: climate.bedroom_ac
    room_sensor: sensor.bedroom_temp
    learning_feedback_delay: 120
```

## Sensor Requirements

### Room Temperature Sensor

The room sensor must:
- Provide numeric temperature values
- Update at least every 5 minutes
- Be placed away from direct airflow
- Not be affected by heat sources

Good sensor placement:
- Wall-mounted at sitting/standing height
- Away from windows and doors
- Not in direct sunlight
- Clear of furniture and obstacles

### Outdoor Temperature Sensor (Optional)

Can be:
- Physical outdoor sensor
- Weather integration sensor
- Must update at least hourly

### Power Sensor (Optional)

Should:
- Monitor the climate device's power consumption
- Report in Watts (W) or kilowatts (kW)
- Update frequently (every 10-60 seconds)
- Have sufficient resolution to detect on/off states

## After Configuration

### Verify Setup

1. Check that your new Smart Climate entity appears in the UI
2. Verify the current temperature shows your room sensor value
3. Test setting a temperature and observe the behavior
4. Check for any errors in the logs

### Enable Learning

1. Find the learning switch entity (e.g., "Living Room Smart AC Learning")
2. Turn on the switch to enable learning
3. Monitor the switch attributes for learning progress

### Next Steps

- [Learn how to use your Smart Climate device](usage.md)
- [Understand the learning system](learning-system.md)
- [Troubleshoot any issues](troubleshooting.md)