# Sensor Reference

This comprehensive guide covers all sensors created by Smart Climate Control, their purposes, placement guidelines, and usage recommendations.

## Table of Contents

1. [Sensor Overview](#sensor-overview)
2. [Complete Sensor Reference](#complete-sensor-reference)
3. [Sensor Requirements and Setup](#sensor-requirements-and-setup)
4. [Sensor Placement Best Practices](#sensor-placement-best-practices)
5. [Dashboard Sensors](#dashboard-sensors-automatically-created)
6. [Choosing Between Internal and Remote Sensors](#choosing-between-internal-and-remote-sensors)
7. [Power Sensor Integration](#power-sensor-integration)
8. [Troubleshooting Sensor Issues](#troubleshooting-sensor-issues)

## Sensor Overview

Smart Climate Control creates **47 comprehensive sensors** that provide deep insights into your system's operation, learning progress, and performance metrics. These sensors are automatically created and organized into logical categories.

### Sensor Categories

- **Core Sensors (12)**: Essential operation metrics
- **Dashboard Sensors (5)**: Automatically created for visualization  
- **Learning & ML Sensors (13)**: Machine learning progress and accuracy
- **Thermal Management Sensors (7)**: Thermal efficiency and state tracking
- **Performance Metrics (6)**: System performance and resource usage
- **System Health Sensors (4)**: Availability and diagnostic information

## Complete Sensor Reference

### Core Sensors

#### Calibration Status
- **Entity**: `sensor.{climate_name}_calibration_status`
- **Values**: `Complete`, `In Progress`, `Not Started`
- **Purpose**: Shows current calibration phase status
- **Usage**: Indicates if system has enough data for predictions

#### Current Accuracy
- **Entity**: `sensor.{climate_name}_current_accuracy`
- **Unit**: %
- **Range**: 0-100%
- **Purpose**: Real-time accuracy of temperature offset predictions
- **Interpretation**:
  - >90% = Excellent predictions
  - 70-90% = Good predictions  
  - 50-70% = Learning in progress
  - <50% = Insufficient data or environmental changes

#### Current Offset
- **Entity**: `sensor.{climate_name}_current_offset`
- **Unit**: °C
- **Range**: Typically -5.0 to +5.0°C
- **Purpose**: The actively applied temperature offset compensation
- **Note**: In PRIMING state, offsets are minimal to avoid disruption

#### Energy Efficiency Score
- **Entity**: `sensor.{climate_name}_energy_efficiency_score`
- **Unit**: /100
- **Range**: 0-100
- **Purpose**: Overall energy efficiency rating based on cycle patterns
- **Calculation**: AC cycle frequency, runtime optimization, temperature stability

#### Hysteresis Cycles
- **Entity**: `sensor.{climate_name}_hysteresis_cycles`
- **Unit**: cycles
- **Purpose**: Number of complete AC on/off cycles recorded
- **Importance**: Required for seasonal learning and pattern detection

#### Hysteresis State
- **Entity**: `sensor.{climate_name}_hysteresis_state`
- **Values**: `Ready`, `Learning`, `No Power Sensor`, `Insufficient Data`
- **Purpose**: Current state of hysteresis learning system

#### Learning Progress
- **Entity**: `sensor.{climate_name}_learning_progress`
- **Unit**: %
- **Range**: 0-100%
- **Purpose**: Overall learning system progress
- **Calculation**: Based on calibration phase completion and sample count

#### Operating Window (Lower/Upper)
- **Entity**: `sensor.{climate_name}_operating_window_lower/upper`
- **Unit**: °C
- **Purpose**: Current temperature comfort boundaries
- **Note**: Adjusts based on thermal state and user preferences

#### Power Correlation Accuracy
- **Entity**: `sensor.{climate_name}_power_correlation_accuracy`
- **Unit**: %
- **Range**: 0-100%
- **Purpose**: Correlation strength between power consumption and temperature changes
- **Interpretation**: >80% indicates reliable power-based state detection

#### Predictive Offset
- **Entity**: `sensor.{climate_name}_predictive_offset`
- **Unit**: °C
- **Purpose**: Weather-based predictive offset adjustment
- **Note**: Requires weather entity configuration

#### Reactive Offset
- **Entity**: `sensor.{climate_name}_reactive_offset`
- **Unit**: °C
- **Purpose**: Real-time reactive offset based on current conditions
- **Note**: Usually matches current_offset in steady state

#### Temperature Window
- **Entity**: `sensor.{climate_name}_temperature_window`
- **Unit**: °C
- **Purpose**: Allowed temperature deviation from setpoint
- **Note**: Tighter in PRIMING state, expands as system learns

### Learning & ML Sensors

#### Mean Absolute Error
- **Entity**: `sensor.{climate_name}_mean_absolute_error`
- **Unit**: °C
- **Purpose**: Average prediction error magnitude
- **Range**: 0-5°C typically
- **Interpretation**: <0.5°C = Excellent

#### Mean Squared Error
- **Entity**: `sensor.{climate_name}_mean_squared_error`
- **Purpose**: Squared prediction errors (penalizes large errors)
- **Note**: More sensitive to outliers than MAE

#### Model Confidence
- **Entity**: `sensor.{climate_name}_model_confidence`
- **Unit**: %
- **Range**: 0-100%
- **Purpose**: Overall ML model confidence
- **Note**: 0% during calibration/PRIMING is normal

#### Model Entropy
- **Entity**: `sensor.{climate_name}_model_entropy`
- **Purpose**: Randomness/uncertainty in predictions
- **Range**: 0-1 (lower = more certain)

#### Momentum Factor
- **Entity**: `sensor.{climate_name}_momentum_factor`
- **Purpose**: Momentum term in gradient descent
- **Range**: 0.0-1.0

#### Outlier Count
- **Entity**: `sensor.{climate_name}_outlier_count`
- **Purpose**: Number of detected data outliers
- **Note**: Outliers are filtered from learning

#### Outlier Detection
- **Entity**: `binary_sensor.{climate_name}_outlier_detection`
- **States**: `on` (outlier detected) / `off` (normal)
- **Purpose**: Real-time outlier detection status

#### Prediction Latency
- **Entity**: `sensor.{climate_name}_prediction_latency`
- **Unit**: ms
- **Purpose**: Time to calculate predictions
- **Target**: <10ms for real-time operation

#### Prediction Variance
- **Entity**: `sensor.{climate_name}_prediction_variance`
- **Purpose**: Variance in recent predictions
- **Note**: Lower = more consistent predictions

#### R-Squared
- **Entity**: `sensor.{climate_name}_r_squared`
- **Range**: 0.0-1.0 (1.0 = perfect fit)
- **Purpose**: Coefficient of determination (model fit quality)
- **Interpretation**: >0.8 = Strong correlation

#### Regularization Strength
- **Entity**: `sensor.{climate_name}_regularization_strength`
- **Purpose**: L2 regularization to prevent overfitting

#### Samples per Day
- **Entity**: `sensor.{climate_name}_samples_per_day`
- **Unit**: samples/d
- **Purpose**: Data collection rate
- **Calculation**: 24 hours × 60 min / update interval

#### Correlation Coefficient
- **Entity**: `sensor.{climate_name}_correlation_coefficient`
- **Range**: -1.0 to 1.0
- **Purpose**: Pearson correlation between predictions and actuals
- **Interpretation**: >0.8 = Strong positive correlation

### Thermal Management Sensors

#### Probing Active
- **Entity**: `sensor.{climate_name}_probing_active`
- **Values**: `Unknown` / `Active` / `Inactive`
- **Purpose**: Whether thermal probing is currently active

#### Shadow Mode
- **Entity**: `sensor.{climate_name}_shadow_mode`
- **Values**: `Unknown` / `Enabled` / `Disabled`
- **Purpose**: Thermal management shadow mode status
- **Note**: Shadow mode learns without actively controlling

#### Tau Cooling
- **Entity**: `sensor.{climate_name}_tau_cooling`
- **Unit**: minutes
- **Range**: 1-1000 minutes
- **Purpose**: Thermal time constant for cooling
- **Note**: PRIMING default: 1.5 min, Typical room: 90-120 min

#### Tau Warming
- **Entity**: `sensor.{climate_name}_tau_warming`
- **Unit**: minutes
- **Range**: 1-1000 minutes
- **Purpose**: Thermal time constant for warming
- **Note**: PRIMING default: 2.5 min, Typical room: 120-180 min

#### Temperature Stability Detected
- **Entity**: `sensor.{climate_name}_temperature_stability_detected`
- **Values**: `Available` / `Not Available`
- **Purpose**: Whether temperature is currently stable

#### Thermal State
- **Entity**: `sensor.{climate_name}_thermal_state`
- **Values**: `priming`, `drifting`, `correcting`, `recovery`, `probing`, `calibrating`
- **Purpose**: Current thermal management state

#### Comfort Preference Level
- **Entity**: `sensor.{climate_name}_comfort_preference_level`
- **Values**: `MAX_COMFORT`, `COMFORT_PRIORITY`, `BALANCED`, `SAVINGS_PRIORITY`, `MAX_SAVINGS`
- **Purpose**: User's comfort vs efficiency preference

### Performance Metrics

#### Memory Usage
- **Entity**: `sensor.{climate_name}_memory_usage`
- **Unit**: KiB
- **Purpose**: Memory consumed by learning system
- **Note**: Typically <100 KiB (very efficient)

#### Persistence Latency
- **Entity**: `sensor.{climate_name}_persistence_latency`
- **Unit**: ms
- **Purpose**: Time to save learning data
- **Target**: <100ms for smooth operation

### System Health Sensors

#### Sensor Availability
- **Entity**: `sensor.{climate_name}_sensor_availability`
- **Unit**: %
- **Range**: 0-100%
- **Purpose**: Percentage of required sensors available
- **Critical**: <100% may impact predictions

### Additional Diagnostic Sensors

The system also provides numerous diagnostic sensors for advanced monitoring:

#### Adaptive Delay
- **Entity**: `sensor.{climate_name}_adaptive_delay`
- **Unit**: seconds
- **Purpose**: Learned delay between temperature adjustment and room response

#### Convergence Trend
- **Entity**: `sensor.{climate_name}_convergence_trend`
- **Values**: `stable`, `improving`, `declining`
- **Purpose**: Direction of prediction accuracy over time

#### Cycle Health
- **Entity**: `sensor.{climate_name}_cycle_health`
- **Values**: `0` (healthy), `1` (warning), `2` (critical)
- **Purpose**: Health indicator for AC cycling patterns

#### Learning Rate
- **Entity**: `sensor.{climate_name}_learning_rate`
- **Range**: 0.0001-0.1 typically
- **Purpose**: Current ML model learning rate

## Sensor Requirements and Setup

### Required Sensors

#### Room Temperature Sensor
- **Must provide**: Numeric temperature values
- **Update frequency**: At least every 5 minutes
- **Accuracy**: ±0.5°C or better recommended
- **Type**: Sensor entity with temperature device class

**Supported Sensor Types**:
- Zigbee temperature sensors (Aqara, Sonoff, etc.)
- Z-Wave temperature sensors
- WiFi sensors (ESPHome, Tasmota)
- Bluetooth sensors (Xiaomi, SwitchBot)
- Integrated sensors (Ecobee, Nest remote sensors)

#### Climate Entity Internal Sensor
- **Purpose**: Provides baseline for offset calculations
- **Access**: Automatic through climate entity
- **Note**: Often inaccurate due to placement near heat sources

### Optional Sensors

#### Outdoor Temperature Sensor
- **Purpose**: Improves offset predictions based on outdoor conditions
- **Requirements**: Shaded from direct sunlight, updates at least hourly
- **Sources**: Physical sensors, weather integrations, local weather stations

#### Power Sensor
- **Purpose**: Enhances learning accuracy and state detection
- **Requirements**: Monitor climate device power, report in Watts, update every 10-60 seconds
- **Types**: Smart plugs, energy monitors, built-in power reporting

## Sensor Placement Best Practices

### Room Temperature Sensor Placement

**Optimal Placement**:
- Mount at 1.2-1.5m (4-5 feet) height
- On interior wall away from exterior walls
- Away from direct sunlight or windows
- Not above heat sources (TVs, lamps, electronics)
- Clear of furniture blocking airflow
- Not in direct AC airflow path

**Avoid Placing Near**:
- Air conditioning vents
- Doorways with drafts
- Kitchen appliances
- Bathrooms with humidity
- Electronic equipment
- Exterior walls

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

## Dashboard Sensors (Automatically Created)

Smart Climate Control automatically creates 5 specialized sensors for dashboard visualization.

### Current Offset Sensor
- **Entity Pattern**: `sensor.{device_name}_offset_current`
- **Purpose**: Real-time temperature offset being applied
- **Device Class**: Temperature
- **Unit**: °C
- **Attributes**: `last_update`, `offset_reason`, `clamped`

### Learning Progress Sensor
- **Entity Pattern**: `sensor.{device_name}_learning_progress`
- **Purpose**: Percentage of learning completion
- **Unit**: %
- **Range**: 0-100%
- **Attributes**: `samples_collected`, `samples_required`, `learning_rate`

### Accuracy Sensor
- **Entity Pattern**: `sensor.{device_name}_accuracy_current`
- **Purpose**: Current prediction accuracy
- **Unit**: %
- **Range**: 0-100%
- **Attributes**: `prediction_error`, `trend`, `confidence_level`

### Calibration Status Sensor
- **Entity Pattern**: `sensor.{device_name}_calibration_status`
- **Purpose**: Shows calibration phase state
- **States**: `calibrating`, `learning`, `complete`
- **Attributes**: `phase_start_time`, `stable_offset_cached`

### Hysteresis State Sensor
- **Entity Pattern**: `sensor.{device_name}_hysteresis_state`
- **Purpose**: AC behavior learning state
- **States**: `idle`, `cooling`, `learning_pattern`
- **Attributes**: `cooling_start_temp`, `cooling_stop_temp`, `pattern_confidence`

### Using Dashboard Sensors

**In Dashboards**:
```yaml
type: gauge
entity: sensor.living_room_smart_ac_learning_progress
name: Learning Progress
min: 0
max: 100
severity:
  green: 80
  yellow: 50
  red: 0
```

**In Automations**:
```yaml
automation:
  - alias: "Notify Learning Complete"
    trigger:
      - platform: state
        entity_id: sensor.living_room_smart_ac_calibration_status
        to: "complete"
    action:
      - service: notify.mobile_app
        data:
          message: "Smart Climate calibration complete!"
```

## Choosing Between Internal and Remote Sensors

### Why Internal Sensors Often Work Better

Counter-intuitively, internal sensors (especially exhaust vent sensors) often provide better results than "somewhat accurate" remote sensors.

#### Key Advantages of Internal Exhaust Sensors

**1. Predictable Offset Patterns**
- During cooling: Reads 10-15°C below room temperature
- When idle: Gradually approaches room temperature
- Pattern is highly predictable and learnable

**2. Clear Operating State Detection**
- Cooling: Immediate sharp drop in temperature
- Idle: Steady rise back toward room temperature
- No ambiguity about operational state

**3. Thermal Dynamics Explanation**
- **During Active Cooling**: Internal fan mixes warm room air with cold evaporator
- **After Cooling Stops**: No airflow mixing, sensor reads pure evaporator temperature
- **Example**: AC target 20.8°C shows 20.8°C while running, drops to 16°C when stopped

**4. Better Learning Potential**
- Larger offsets provide clearer signals
- More data points across wider range
- Clearer correlation patterns
- Faster convergence to optimal offsets

### When to Use Internal vs Remote Sensors

#### Use Internal Sensors When:
- Internal sensor is at exhaust vent (reads very cold during cooling)
- You want most accurate learning over time
- Offset is large but consistent
- You have good room temperature sensor placement

#### Consider Remote Sensors When:
- Remote sensor significantly more accurate than internal
- Internal sensor has erratic, unpredictable behavior
- Remote sensor is in better location than room sensor
- You don't plan to use learning features

### Configuration Tips for Exhaust Sensors

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
- **Higher max_offset**: Exhaust sensors need larger ranges (10-20°C)
- **Enable learning**: Predictable patterns make learning highly effective
- **Moderate learning_rate**: 0.2-0.4 works well for consistent patterns

## Power Sensor Integration

### Power Consumption Patterns

Understanding your AC's power patterns helps configure thresholds:

**Typical Patterns**:
- **Idle**: 50-200W (control circuits only)
- **Fan Only**: 100-300W
- **Cooling**: 500-3000W (depends on size)
- **Startup Spike**: 2-5x running power (brief)

### Configurable Power Thresholds

Smart Climate supports three configurable power thresholds:

#### Power Idle Threshold
- **Purpose**: Power consumption below this indicates AC is idle or off
- **Default**: 50W
- **Range**: 10-500W
- **Example**: Set to 30W for small window units, 100W for large central systems

#### Power Min Threshold
- **Purpose**: Power consumption below this indicates AC running at minimum
- **Default**: 100W
- **Range**: 50-1000W
- **Example**: Set to 80W for small units, 300W for large systems

#### Power Max Threshold
- **Purpose**: Power consumption above this indicates AC running at high/max
- **Default**: 250W
- **Range**: 100-5000W
- **Example**: Set to 600W for small units, 3000W for large systems

### How Power States Work

1. **Power < Idle Threshold**: AC is off or standby
2. **Idle < Power < Min Threshold**: AC on but minimal operation
3. **Min < Power < Max Threshold**: AC cooling moderately
4. **Power > Max Threshold**: AC working at maximum

### Configuration Examples by AC Type

#### Small Window Units (5,000-8,000 BTU)
```yaml
power_idle_threshold: 30    # Lower standby power
power_min_threshold: 80     # Smaller compressor
power_max_threshold: 600    # Max around 600-800W
```

#### Medium Split Systems (12,000-18,000 BTU)
```yaml
power_idle_threshold: 50    # Default values work well
power_min_threshold: 100    
power_max_threshold: 1200   # Higher max power
```

#### Large Central AC (24,000+ BTU)
```yaml
power_idle_threshold: 100   # Control circuits use more
power_min_threshold: 300    # Larger fans
power_max_threshold: 3000   # Much higher cooling power
```

## Troubleshooting Sensor Issues

### Common Problems and Solutions

#### Sensor Shows Unavailable
- Check network connectivity (WiFi/Zigbee)
- Verify battery levels
- Check integration status
- Review logs for errors

#### Erratic Readings
- Check for interference sources
- Verify sensor placement
- Consider filtering
- Replace batteries if applicable

#### Slow Updates
- Check sensor polling intervals
- Verify network reliability
- Consider sensor firmware updates
- Review integration settings

#### Offset Calculations Seem Wrong
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

Monitor sensor readings:
```
DEBUG: Room temperature: 22.5°C (sensor.living_room_temperature)
DEBUG: AC internal temperature: 20.8°C
DEBUG: Outdoor temperature: 28.3°C (sensor.outdoor_temperature)
DEBUG: Power consumption: 1250W (sensor.ac_power)
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

## Understanding Sensor Relationships

### During PRIMING State (First 24-48 hours)
- Tau values: 1.5/2.5 minutes (conservative defaults)
- Offsets: Minimal (-0.1°C typical)
- Confidence: 0% (building baseline)
- Temperature window: ±0.2°C (tight control)

### After Calibration
- Tau values: 90/150 minutes (realistic room physics)
- Offsets: Dynamic based on conditions
- Confidence: Increases with data (target >80%)
- Temperature window: Expands based on preference

### Healthy System Indicators
- Current Accuracy: >80%
- R-Squared: >0.7
- Correlation Coefficient: >0.7
- Cycle Health: 0
- Average cycles: >10 minutes
- Memory Usage: <100 KiB
- Sensor Availability: 100%

### Warning Signs
- Accuracy dropping below 50%
- Cycle Health: 1 or 2 (short cycling)
- Average cycles: <7 minutes
- Outlier Count: Increasing rapidly
- Sensor Availability: <100%

## Sensor Update Frequencies

- **Real-time** (every coordinator update): Current values, offsets, temperatures
- **Every 5 minutes**: Learning samples, ML metrics
- **Every 60 minutes**: Persistence, seasonal data
- **On AC state change**: Hysteresis, cycles, thermal state
- **Daily**: Thermal probing (during calibration window)

## Best Practices Summary

1. **Prioritize Room Sensor Quality**: Invest in accurate, responsive sensors
2. **Optimal Placement**: Follow placement guidelines for best results
3. **Regular Calibration**: Check and calibrate sensors periodically
4. **Monitor Availability**: Set up alerts for sensor failures
5. **Use Filtering**: Apply filters for noisy sensors
6. **Consider Redundancy**: Multiple sensors for critical areas
7. **Leverage Dashboard Sensors**: Use automatic sensors for monitoring

---

*Complete sensor understanding leads to optimal Smart Climate performance!*