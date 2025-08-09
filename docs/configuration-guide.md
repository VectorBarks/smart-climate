# Configuration Guide

This comprehensive guide covers all configuration options for Smart Climate Control, including UI settings, YAML configuration, and optimization parameters.

## Table of Contents

1. [Configuration Methods](#configuration-methods)
2. [UI Configuration](#ui-configuration-complete-settings)
3. [YAML Configuration](#yaml-configuration-advanced-users)
4. [Configuration Parameters Reference](#configuration-parameters-reference)
5. [Gradual Adjustment Rate Guide](#gradual-adjustment-rate-guide)
6. [Update Interval Configuration](#update-interval-configuration)
7. [Power Threshold Configuration](#power-threshold-configuration)
8. [Advanced Features Configuration](#advanced-features-configuration)
9. [Complete Configuration Examples](#complete-configuration-examples)

## Configuration Methods

Smart Climate Control supports two configuration approaches:

- **UI Configuration** (Recommended): Complete setup through Home Assistant interface with ALL settings available
- **YAML Configuration** (Advanced): Text-based configuration for advanced users or bulk setup

The UI configuration now provides access to ALL settings, making it the preferred method for most users.

## UI Configuration (Complete Settings)

### Step 1: Add Integration

1. Navigate to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "Smart Climate Control"
4. Click on the integration to start configuration

### Step 2: Basic Configuration

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
- Helps detect when AC is actively cooling vs idle
- Enhances learning accuracy and state detection
- Example: `sensor.ac_power`, `sensor.smart_plug_power`

### Step 3: Comprehensive Settings Configuration

All configuration options are now available in the UI:

#### Basic Settings

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Maximum Offset** | Maximum temperature adjustment allowed | 5.0°C | 1.0 - 10.0°C |
| **Minimum Temperature** | Lowest allowed setpoint | 16°C | 10 - 25°C |
| **Maximum Temperature** | Highest allowed setpoint | 30°C | 20 - 35°C |
| **Update Interval** | How often to recalculate offsets | 180s | 60 - 600s |
| **ML Enabled** | Enable machine learning features | True | True/False |

#### Mode Settings

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Away Temperature** | Fixed temperature for away mode | 26°C | 10 - 35°C |
| **Sleep Mode Offset** | Additional offset for quieter night operation | 1.0°C | -5.0 to +5.0°C |
| **Boost Mode Offset** | Extra cooling offset for rapid temperature reduction | -2.0°C | -10.0 to 0°C |

#### Advanced Settings

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Gradual Adjustment Rate** | Temperature change per update cycle | 0.5°C | 0.1 - 2.0°C |
| **Learning Feedback Delay** | Time to wait before measuring AC response | 45s | 10 - 300s |
| **Enable Learning** | Start with learning system active | False | True/False |
| **Data Retention Days** | Days of historical data to keep | 60 | 30 - 365 |

#### Data Quality Features

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Outlier Detection** | Detect and filter sensor malfunctions | True | True/False |
| **Outlier Sensitivity** | Z-score threshold for detection | 2.5 | 1.0 - 5.0 |

#### Weather Integration (v1.3.0+)

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Adaptive Delay** | Learn optimal feedback timing automatically | False | True/False |
| **Weather Entity** | Weather integration for forecast predictions | None | Weather entities |
| **Seasonal Learning** | Adapt to outdoor temperature patterns | Auto* | True/False |

*Auto-enabled when outdoor sensor is configured

#### Power Sensor Settings (Only visible when power sensor configured)

| Setting | Description | Default | Range |
|---------|-------------|---------|-------|
| **Power Idle Threshold** | Power consumption below this = AC idle/off | 50W | 10 - 500W |
| **Power Min Threshold** | Power consumption below this = AC at minimum | 100W | 50 - 1000W |
| **Power Max Threshold** | Power consumption above this = AC at high/max | 250W | 100 - 5000W |

### Step 4: Options Flow (Modify After Setup)

After initial setup, modify ALL settings through the Options flow:

1. Go to Settings → Devices & Services
2. Find your Smart Climate integration
3. Click "Configure"
4. Modify any setting through the comprehensive UI
5. Click "Submit" to apply changes

The options flow provides the same comprehensive settings as initial setup.

## YAML Configuration (Advanced Users)

While the UI provides access to all settings, YAML configuration remains available for advanced users.

### Basic Configuration

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
    
  # Multiple climate devices
  - name: "Bedroom Smart AC"
    climate_entity: climate.bedroom_ac
    room_sensor: sensor.bedroom_temperature
    sleep_offset: 2.0  # Higher offset for bedroom comfort
```

## Configuration Parameters Reference

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
| `ml_enabled` | boolean | No | true | Enable machine learning features |
| `away_temperature` | float | No | 26 | Temperature for away mode (°C) |
| `sleep_offset` | float | No | 1.0 | Additional offset for sleep mode (°C) |
| `boost_offset` | float | No | -2.0 | Additional cooling for boost mode (°C) |
| `gradual_adjustment_rate` | float | No | 0.5 | Temperature change per update (°C) |
| `enable_learning` | boolean | No | false | Enable learning on startup |
| `data_retention_days` | integer | No | 60 | Days to retain learning data |
| `learning_feedback_delay` | integer | No | 45 | Delay before feedback collection (seconds) |
| `power_idle_threshold` | integer | No | 50 | Power threshold for idle state (W) |
| `power_min_threshold` | integer | No | 100 | Power threshold for minimum operation (W) |
| `power_max_threshold` | integer | No | 250 | Power threshold for maximum operation (W) |

## Gradual Adjustment Rate Guide

The gradual adjustment rate controls how quickly Smart Climate adjusts your AC's target temperature to reach your desired room temperature.

### Understanding Rate Impact

The gradual adjustment rate determines the **maximum temperature change** Smart Climate can apply during each update cycle (default: every 180 seconds).

**Rate Examples for 2°C correction**:
- **1.0°C**: Reaches target in 6-10 minutes (aggressive)
- **0.5°C**: Reaches target in 12-20 minutes (balanced - default)
- **0.25°C**: Reaches target in 25-40 minutes (gentle)
- **0.1°C**: Reaches target in 60+ minutes (ultra-gentle)

### Room-Specific Recommendations

#### Bedrooms
**Recommended Rate**: 0.1 - 0.3°C
```yaml
gradual_adjustment_rate: 0.2
```
**Why**: Sleep quality requires stable temperatures. Slow adjustments prevent waking from temperature changes.

#### Living Rooms
**Recommended Rate**: 0.4 - 0.6°C (Default)
```yaml
gradual_adjustment_rate: 0.5  # Default
```
**Why**: Balance between comfort and responsiveness for varied activities.

#### Kitchens
**Recommended Rate**: 0.7 - 1.2°C
```yaml
gradual_adjustment_rate: 1.0
```
**Why**: Rapid heat generation from cooking requires quick response.

#### Home Offices
**Recommended Rate**: 0.2 - 0.4°C
```yaml
gradual_adjustment_rate: 0.3
```
**Why**: Stable temperature improves focus and productivity.

### AC Type Considerations

#### Inverter/Variable Speed ACs
**Recommended Rate**: 0.1 - 0.4°C
- Designed for continuous micro-adjustments
- Most efficient with small changes
- Quieter operation with gentle rates

#### Traditional On/Off ACs
**Recommended Rate**: 0.5 - 1.0°C
- Need larger changes to trigger cycling
- Better response with decisive changes
- Avoid rates below 0.3°C

#### Central Systems
**Recommended Rate**: 0.3 - 0.7°C
- Multiple zones complicate response
- Ductwork adds thermal lag
- Account for furthest room from unit

### Energy Impact

| Rate | Relative Energy Use | Comfort Level | Response Time |
|------|-------------------|---------------|---------------|
| 0.1°C | 70-80% (Best) | Very Stable | Very Slow |
| 0.25°C | 80-85% | Stable | Slow |
| 0.5°C | 90-95% (Baseline) | Balanced | Moderate |
| 0.75°C | 95-105% | Variable | Fast |
| 1.0°C | 105-120% (Worst) | Unstable | Very Fast |

## Update Interval Configuration

The update interval determines how frequently Smart Climate recalculates offsets and adjusts your AC's target temperature.

### Relationship with Adjustment Rate

These settings work together:
```
Maximum °C/hour = (gradual_adjustment_rate × 3600) / update_interval
```

### AC Type Recommendations

#### Inverter/Variable Speed ACs
**Optimal Settings**:
```yaml
update_interval: 90  # 1.5 minutes
gradual_adjustment_rate: 0.2  # Small steps
```

**Benefits**:
- Compressor stays at steady speed
- 15-25% more efficient than defaults
- Quieter operation
- Less mechanical wear

#### Traditional On/Off ACs
**Optimal Settings**:
```yaml
update_interval: 180  # 3 minutes (default)
gradual_adjustment_rate: 0.5  # Standard steps
```

**Benefits**:
- Prevents short cycling
- Clear on/off signals
- Reduces start/stop wear

### Room-Specific Configurations

#### Bedrooms (Priority: Stability)
```yaml
# For Inverter AC
update_interval: 120
gradual_adjustment_rate: 0.2

# For Traditional AC
update_interval: 240
gradual_adjustment_rate: 0.4
```

#### Kitchens (Priority: Quick Response)
```yaml
# For Inverter AC
update_interval: 60
gradual_adjustment_rate: 0.3

# For Traditional AC
update_interval: 120
gradual_adjustment_rate: 0.7
```

### Efficiency Analysis

**Inverter AC Comparison**: 90s/0.2°C vs 180s/0.5°C (Default)

**Energy Savings**:
- Default: 6.4 kWh/day = $0.96/day
- Optimized: 5.0 kWh/day = $0.75/day  
- **Savings: $77/year**

**Efficiency Gains**:
- Compressor efficiency: +20%
- Reduced overshoot: +10%
- Less cycling loss: +5%
- **Total: +15-25%**

## Power Threshold Configuration

Power thresholds are crucial for accurate AC state detection and optimal learning performance.

### Understanding Power Thresholds

The system uses power consumption patterns to understand AC behavior:

- **Idle Threshold**: Power when AC is in standby or off
- **Min Threshold**: Power when AC is running at minimum capacity
- **Max Threshold**: Power when AC is running at high/maximum capacity

### Configuration Examples by AC Type

#### Small Window/Portable Units (500-800W)
```yaml
power_idle_threshold: 5      # Standby: 3-5W
power_min_threshold: 80     # Minimum cooling: 80-120W
power_max_threshold: 600    # Maximum cooling: 500-800W
```

#### Medium Split Systems (1000-2000W)
```yaml
power_idle_threshold: 10     # Standby: 5-15W
power_min_threshold: 150    # Minimum cooling: 150-300W
power_max_threshold: 1500   # Maximum cooling: 1200-2000W
```

#### Large Central/Multi-zone Systems (2000-5000W)
```yaml
power_idle_threshold: 20     # Standby: 10-30W
power_min_threshold: 400    # Minimum cooling: 400-800W
power_max_threshold: 4000   # Maximum cooling: 3000-5000W
```

### Determining Your AC's Power Values

#### Method 1: Using Home Assistant History
1. Enable your power sensor and let it run for a few cooling cycles
2. Go to Developer Tools → Statistics
3. Select your power sensor
4. Observe patterns:
   - Lowest values (AC off) = Idle power
   - Consistent low values (AC just started) = Minimum power
   - Highest sustained values = Maximum power

#### Method 2: Real-time Observation
1. Turn off AC completely and wait 1 minute → **Idle power**
2. Set AC to cool with high temperature difference → **Minimum power**
3. Wait for AC to reach full cooling → **Maximum power**

### Setting Optimal Thresholds

#### General Guidelines

1. **Idle Threshold**: Set 2-3x higher than actual standby power
2. **Min Threshold**: Set 10-20% below typical minimum running power
3. **Max Threshold**: Set at 70-80% of actual maximum power

#### Safety Margins
Always leave margins between thresholds:
- Idle to Min: At least 50W gap
- Min to Max: At least 200W gap

### Troubleshooting Power Thresholds

#### Symptoms of Incorrect Thresholds
1. **Learning not collecting data**: Idle threshold too high
2. **Constant "high power" state**: Max threshold too low
3. **Never sees "idle" state**: Idle threshold too low
4. **Erratic state changes**: Thresholds too close together

#### Debug Mode
```yaml
logger:
  default: info
  logs:
    custom_components.smart_climate.offset_engine: debug
```

Look for messages like:
```
Power state: idle (3W < 10W threshold)
Power state: moderate (450W between 200W and 1000W)
Power transition detected: idle -> moderate
```

## Advanced Features Configuration

### Adaptive Feedback Delays (v1.3.0+)

Learn optimal timing for your specific AC unit's response characteristics.

#### UI Configuration
Enable "Adaptive Delay" in the UI configuration options.

#### YAML Configuration
```yaml
smart_climate:
  - name: "Living Room AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temp
    adaptive_delay: true  # Enable adaptive delay learning
```

**How It Works**:
- Monitors temperature changes every 15 seconds after HVAC mode changes
- Detects stabilization when temperature change < 0.1°C
- Uses exponential moving average to refine learned delays
- Applies 5-second safety buffer to all learned delays

**Benefits**:
- **Modern inverter ACs**: Usually learn delays of 20-40 seconds
- **Standard ACs**: Typically learn delays of 45-90 seconds
- **Older systems**: May learn delays of 60-180 seconds

### Weather Forecast Integration (v1.3.0+)

Predictive temperature adjustments based on upcoming weather conditions.

#### Basic YAML Configuration
```yaml
smart_climate:
  - name: "Living Room AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temp
    weather_entity: weather.home  # Your weather integration
```

#### Advanced Strategy Configuration
```yaml
smart_climate:
  - name: "Living Room AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temp
    weather_entity: weather.home
    forecast_strategies:
      - type: "heat_wave"
        enabled: true
        trigger_temp: 30.0      # °C threshold for heat wave
        trigger_duration: 3     # Hours of high temp required
        adjustment: -1.0        # Temperature adjustment (°C)
        max_duration: 8         # Maximum strategy duration (hours)
      - type: "clear_sky"
        enabled: true
        conditions: ["sunny", "clear", "clear-night"]
        adjustment: -0.5        # Thermal optimization adjustment
        max_duration: 6         # Maximum strategy duration
```

#### Strategy Types

**Heat Wave Strategy**:
- **Purpose**: Pre-cooling before extreme heat
- **Best for**: Hot climates, poor insulation, east/west-facing rooms

**Clear Sky Strategy**:
- **Purpose**: Thermal optimization during clear weather  
- **Best for**: Buildings with significant solar heat gain

### Seasonal Adaptation (v1.3.0+)

Context-aware learning that adapts to outdoor temperature patterns.

#### YAML Configuration
```yaml
smart_climate:
  - name: "Living Room AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temp
    outdoor_sensor: sensor.outdoor_temperature  # Required
    seasonal_learning: true  # Auto-enabled when outdoor sensor present
```

**How It Works**:
- Groups learned AC patterns by outdoor temperature ranges (5°C buckets)
- Retains 45 days of seasonal data for pattern matching
- Uses median calculations for robust predictions
- Requires minimum 3 samples per temperature bucket

**Benefits**:
- **Spring/Fall**: Better accuracy during temperature transitions
- **Summer**: Adapts to heat load patterns based on outdoor temperature
- **Winter**: Heating mode optimization (if applicable)
- **All seasons**: More relevant pattern matching for current conditions

## Complete Configuration Examples

### Basic Setup (Recommended)
```yaml
smart_climate:
  - name: "Living Room Climate"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
```

### Full Featured Setup (v1.3.0+)
```yaml
smart_climate:
  - name: "Master Bedroom Climate"
    climate_entity: climate.master_bedroom_ac
    room_sensor: sensor.master_bedroom_temperature
    outdoor_sensor: sensor.outdoor_temperature
    power_sensor: sensor.ac_power_consumption
    weather_entity: weather.home
    
    # Core settings
    max_offset: 4.0
    min_temperature: 18
    max_temperature: 28
    update_interval: 120
    
    # Learning configuration
    ml_enabled: true
    enable_learning: true
    adaptive_delay: true
    seasonal_learning: true
    learning_feedback_delay: 60
    data_retention_days: 90
    
    # Mode settings  
    away_temperature: 27
    sleep_offset: 1.5
    boost_offset: -2.5
    gradual_adjustment_rate: 0.3
    
    # Power thresholds
    power_idle_threshold: 30
    power_min_threshold: 200  
    power_max_threshold: 1200
    
    # Weather strategies
    forecast_strategies:
      - type: "heat_wave"
        enabled: true
        trigger_temp: 32.0
        trigger_duration: 2
        adjustment: -1.5
        max_duration: 6
```

### Multi-Zone Setup
```yaml
smart_climate:
  # Living room with full features
  - name: "Living Room Climate"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    outdoor_sensor: sensor.outdoor_temperature
    power_sensor: sensor.living_room_ac_power
    weather_entity: weather.home
    adaptive_delay: true
    seasonal_learning: true
    
  # Bedroom with basic setup
  - name: "Master Bedroom Climate"  
    climate_entity: climate.master_bedroom_ac
    room_sensor: sensor.master_bedroom_temperature
    gradual_adjustment_rate: 0.2  # Gentler for sleeping
    sleep_offset: 2.0
    
  # Guest room minimal setup
  - name: "Guest Room Climate"
    climate_entity: climate.guest_room_ac
    room_sensor: sensor.guest_room_temperature
    away_temperature: 28  # Higher for unoccupied room
```

## Best Practices

### Initial Configuration
1. Start with default settings and UI configuration
2. Add optional sensors (outdoor, power) for enhanced features
3. Enable learning after verifying basic operation
4. Monitor performance for 1-2 weeks before optimization

### Optimization Process
1. **Start with defaults** for your AC type
2. **Monitor for 1 week** - track comfort complaints, response times, energy usage
3. **Adjust by ±0.1°C** for gradual adjustment rate
4. **Test for 3-4 days** before further changes
5. **Repeat until optimal**

### Signs of Correct Configuration
- Room reaches target without overshoot
- Temperature remains stable once reached
- AC doesn't short cycle
- Energy usage reasonable
- Occupants comfortable

## Next Steps

After configuration:
- [Learn daily usage](user-guide.md) for optimal operation
- [Understand sensors](sensor-reference.md) for monitoring
- [Explore technical details](technical-reference.md) for advanced features

---

*Perfect configuration leads to optimal comfort and efficiency!*