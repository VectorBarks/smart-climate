# Smart Climate Control - Comprehensive Sensor Documentation

This document provides detailed explanations of all 47 sensors exposed by Smart Climate Control v1.4.1+, organized by category with real-world examples and expected values.

## Table of Contents
1. [Core Sensors](#core-sensors)
2. [Diagnostic Sensors](#diagnostic-sensors)
3. [Learning & ML Sensors](#learning--ml-sensors)
4. [Thermal Management Sensors](#thermal-management-sensors)
5. [Performance Metrics](#performance-metrics)
6. [System Health Sensors](#system-health-sensors)
7. [AC Behavior Sensors](#ac-behavior-sensors)

---

## Core Sensors

### Calibration Status
- **Entity**: `sensor.{climate_name}_calibration_status`
- **Description**: Shows the current calibration phase status
- **Values**: 
  - `Complete` - Initial calibration finished (10+ samples collected)
  - `In Progress` - Currently collecting initial samples
  - `Not Started` - No samples collected yet
- **Example**: `Complete`
- **Usage**: Indicates if the system has enough data to start making predictions

### Current Accuracy
- **Entity**: `sensor.{climate_name}_current_accuracy`
- **Unit**: %
- **Description**: Real-time accuracy of temperature offset predictions
- **Range**: 0-100%
- **Example**: `93%`
- **Interpretation**: 
  - >90% = Excellent predictions
  - 70-90% = Good predictions
  - 50-70% = Learning in progress
  - <50% = Insufficient data or environmental changes

### Current Offset
- **Entity**: `sensor.{climate_name}_current_offset`
- **Unit**: °C
- **Description**: The actively applied temperature offset compensation
- **Range**: Typically -5.0 to +5.0°C
- **Example**: `-0.1°C`
- **Note**: In PRIMING state, offsets are minimal to avoid disruption

### Energy Efficiency Score
- **Entity**: `sensor.{climate_name}_energy_efficiency_score`
- **Unit**: /100
- **Description**: Overall energy efficiency rating based on cycle patterns and runtime
- **Range**: 0-100
- **Example**: `80/100`
- **Calculation**: Based on:
  - AC cycle frequency (fewer cycles = better)
  - Runtime duration (optimized runtime = better)
  - Temperature stability (less overshoot = better)

### Hysteresis Cycles
- **Entity**: `sensor.{climate_name}_hysteresis_cycles`
- **Unit**: cycles
- **Description**: Number of complete AC on/off cycles recorded
- **Example**: `36 cycles`
- **Importance**: Required for seasonal learning and pattern detection

### Hysteresis State
- **Entity**: `sensor.{climate_name}_hysteresis_state`
- **Description**: Current state of hysteresis learning system
- **Values**:
  - `Ready` - System ready to record next cycle
  - `Learning` - Currently recording AC cycle
  - `No Power Sensor` - Power monitoring not configured
  - `Insufficient Data` - <3 cycles recorded
- **Example**: `Ready`

### Learning Progress
- **Entity**: `sensor.{climate_name}_learning_progress`
- **Unit**: %
- **Description**: Overall learning system progress
- **Range**: 0-100%
- **Example**: `100%`
- **Calculation**: Based on calibration phase completion and sample count

### Operating Window (Lower/Upper)
- **Entity**: `sensor.{climate_name}_operating_window_lower/upper`
- **Unit**: °C
- **Description**: Current temperature comfort boundaries
- **Example**: `22.5°C / 25.5°C`
- **Note**: Adjusts based on thermal state and user preferences

### Power Correlation Accuracy
- **Entity**: `sensor.{climate_name}_power_correlation_accuracy`
- **Unit**: %
- **Description**: Correlation strength between power consumption and temperature changes
- **Range**: 0-100%
- **Example**: `85%`
- **Interpretation**: >80% indicates reliable power-based state detection

### Predictive Offset
- **Entity**: `sensor.{climate_name}_predictive_offset`
- **Unit**: °C
- **Description**: Weather-based predictive offset adjustment
- **Example**: `0.0°C`
- **Note**: Requires weather entity configuration

### Reactive Offset
- **Entity**: `sensor.{climate_name}_reactive_offset`
- **Unit**: °C
- **Description**: Real-time reactive offset based on current conditions
- **Example**: `-0.1°C`
- **Note**: Usually matches current_offset in steady state

### Temperature Window
- **Entity**: `sensor.{climate_name}_temperature_window`
- **Unit**: °C
- **Description**: Allowed temperature deviation from setpoint
- **Example**: `±0.2°C`
- **Note**: Tighter in PRIMING state, expands as system learns

---

## Diagnostic Sensors

### Adaptive Delay
- **Entity**: `sensor.{climate_name}_adaptive_delay`
- **Unit**: seconds
- **Description**: Learned delay between temperature adjustment and room response
- **Range**: 0-3600s (0-60 minutes)
- **Example**: `0.0s`
- **Note**: Learns optimal feedback timing for your specific HVAC

### Adjusted Comfort Band
- **Entity**: `sensor.{climate_name}_adjusted_comfort_band`
- **Unit**: °C
- **Description**: Current comfort band width after all adjustments
- **Range**: 0.5-3.0°C typically
- **Example**: `1.50°C`
- **Factors**: User preference, outdoor temperature, thermal state

### Average Off/On Cycle
- **Entity**: `sensor.{climate_name}_average_off_cycle` and `_average_on_cycle`
- **Unit**: minutes or "Unknown"
- **Description**: Average duration of AC off and on periods
- **Example**: `Unknown` (no cycles yet)
- **Healthy Range**: 
  - On: 10-30 minutes
  - Off: 15-45 minutes
  - <7 minutes indicates short cycling

### Comfort Preference Level
- **Entity**: `sensor.{climate_name}_comfort_preference_level`
- **Description**: User's comfort vs efficiency preference
- **Values**:
  - `MAX_COMFORT` - Tightest control, highest energy use
  - `COMFORT_PRIORITY` - Comfort-focused with some efficiency
  - `BALANCED` - Default, balances comfort and efficiency
  - `SAVINGS_PRIORITY` - Energy-focused with acceptable comfort
  - `MAX_SAVINGS` - Maximum efficiency, wider temperature swings
- **Example**: `BALANCED`

### Convergence Trend
- **Entity**: `sensor.{climate_name}_convergence_trend`
- **Description**: Direction of prediction accuracy over time
- **Values**:
  - `stable` - Accuracy consistent
  - `improving` - Getting more accurate
  - `declining` - Losing accuracy (environmental change?)
- **Example**: `stable`

### Cycle Health
- **Entity**: `sensor.{climate_name}_cycle_health`
- **Description**: Health indicator for AC cycling patterns
- **Values**:
  - `0` - No data or healthy cycles
  - `1` - Warning: short cycling detected
  - `2` - Critical: severe short cycling
- **Example**: `0`

### EMA Coefficient
- **Entity**: `sensor.{climate_name}_ema_coefficient`
- **Description**: Exponential Moving Average smoothing factor
- **Range**: 0.0-1.0
- **Example**: `0.2`
- **Note**: Higher = more responsive to recent changes

### Last Probe Result
- **Entity**: `sensor.{climate_name}_last_probe_result`
- **Description**: Result of last thermal probe operation
- **Values**: `Not Available` or probe details
- **Example**: `Not Available`

### Learned Delay
- **Entity**: `sensor.{climate_name}_learned_delay`
- **Unit**: seconds
- **Description**: System's learned response delay
- **Example**: `0.00s`

### Learning Rate
- **Entity**: `sensor.{climate_name}_learning_rate`
- **Description**: Current ML model learning rate
- **Range**: 0.0001-0.1 typically
- **Example**: `0.001`

---

## Learning & ML Sensors

### Mean Absolute Error
- **Entity**: `sensor.{climate_name}_mean_absolute_error`
- **Unit**: °C
- **Description**: Average prediction error magnitude
- **Range**: 0-5°C typically
- **Example**: `0.013`
- **Interpretation**: <0.5°C = Excellent

### Mean Squared Error
- **Entity**: `sensor.{climate_name}_mean_squared_error`
- **Description**: Squared prediction errors (penalizes large errors)
- **Example**: `0.007`
- **Note**: More sensitive to outliers than MAE

### Model Confidence
- **Entity**: `sensor.{climate_name}_model_confidence`
- **Unit**: %
- **Description**: Overall ML model confidence
- **Range**: 0-100%
- **Example**: `0.0%`
- **Note**: 0% during calibration/PRIMING is normal

### Model Entropy
- **Entity**: `sensor.{climate_name}_model_entropy`
- **Description**: Randomness/uncertainty in predictions
- **Range**: 0-1 (lower = more certain)
- **Example**: `-0.647`

### Momentum Factor
- **Entity**: `sensor.{climate_name}_momentum_factor`
- **Description**: Momentum term in gradient descent
- **Range**: 0.0-1.0
- **Example**: `0.900`

### Outlier Count
- **Entity**: `sensor.{climate_name}_outlier_count`
- **Description**: Number of detected data outliers
- **Example**: `0`
- **Note**: Outliers are filtered from learning

### Outlier Detection
- **Entity**: `binary_sensor.{climate_name}_outlier_detection`
- **Description**: Real-time outlier detection status
- **States**: `on` (outlier detected) / `off` (normal)
- **Example**: `Ein` (German for "on")

### Prediction Latency
- **Entity**: `sensor.{climate_name}_prediction_latency`
- **Unit**: ms
- **Description**: Time to calculate predictions
- **Example**: `1ms`
- **Target**: <10ms for real-time operation

### Prediction Variance
- **Entity**: `sensor.{climate_name}_prediction_variance`
- **Description**: Variance in recent predictions
- **Example**: `0.003`
- **Note**: Lower = more consistent predictions

### R-Squared
- **Entity**: `sensor.{climate_name}_r_squared`
- **Description**: Coefficient of determination (model fit quality)
- **Range**: 0.0-1.0 (1.0 = perfect fit)
- **Example**: `0.840`
- **Interpretation**: >0.8 = Strong correlation

### Regularization Strength
- **Entity**: `sensor.{climate_name}_regularization_strength`
- **Description**: L2 regularization to prevent overfitting
- **Example**: `0.001`

### Samples per Day
- **Entity**: `sensor.{climate_name}_samples_per_day`
- **Unit**: samples/d
- **Description**: Data collection rate
- **Example**: `288.0 samples/d`
- **Calculation**: 24 hours × 60 min / 5 min interval = 288

---

## Thermal Management Sensors

### Probing Active
- **Entity**: `sensor.{climate_name}_probing_active`
- **Description**: Whether thermal probing is currently active
- **Values**: `Unknown` / `Active` / `Inactive`
- **Example**: `Unknown`

### Shadow Mode
- **Entity**: `sensor.{climate_name}_shadow_mode`
- **Description**: Thermal management shadow mode status
- **Values**: `Unknown` / `Enabled` / `Disabled`
- **Example**: `Unknown`
- **Note**: Shadow mode learns without actively controlling

### Tau Cooling
- **Entity**: `sensor.{climate_name}_tau_cooling`
- **Unit**: minutes
- **Description**: Thermal time constant for cooling
- **Range**: 1-1000 minutes
- **Example**: `1.5 min`
- **Note**: 
  - PRIMING default: 1.5 min
  - Typical room: 90-120 min
  - Auto-adjusts after probing

### Tau Warming
- **Entity**: `sensor.{climate_name}_tau_warming`
- **Unit**: minutes
- **Description**: Thermal time constant for warming
- **Range**: 1-1000 minutes
- **Example**: `2.5 min`
- **Note**:
  - PRIMING default: 2.5 min
  - Typical room: 120-180 min
  - Usually higher than tau_cooling

### Temperature Stability Detected
- **Entity**: `sensor.{climate_name}_temperature_stability_detected`
- **Description**: Whether temperature is currently stable
- **Values**: `Available` / `Not Available`
- **Example**: `Available`

### Thermal State
- **Entity**: `sensor.{climate_name}_thermal_state`
- **Description**: Current thermal management state
- **Values**:
  - `priming` - Initial conservative learning (24-48h)
  - `drifting` - AC off, temperature drifting
  - `correcting` - AC on, correcting temperature
  - `recovery` - Recovering from mode change
  - `probing` - Active thermal characteristic learning
  - `calibrating` - Fine-tuning offsets
- **Example**: `priming`

---

## Performance Metrics

### Correlation Coefficient
- **Entity**: `sensor.{climate_name}_correlation_coefficient`
- **Description**: Pearson correlation between predictions and actuals
- **Range**: -1.0 to 1.0
- **Example**: `0.867`
- **Interpretation**: >0.8 = Strong positive correlation

### Memory Usage
- **Entity**: `sensor.{climate_name}_memory_usage`
- **Unit**: KiB
- **Description**: Memory consumed by learning system
- **Example**: `14.8 KiB`
- **Note**: Typically <100 KiB (very efficient)

### Persistence Latency
- **Entity**: `sensor.{climate_name}_persistence_latency`
- **Unit**: ms
- **Description**: Time to save learning data
- **Example**: `27.8 ms`
- **Target**: <100ms for smooth operation

---

## System Health Sensors

### Sensor Availability
- **Entity**: `sensor.{climate_name}_sensor_availability`
- **Unit**: %
- **Description**: Percentage of required sensors available
- **Range**: 0-100%
- **Example**: `100.0%`
- **Critical**: <100% may impact predictions

---

## AC Behavior Sensors

### Seasonal Adaptation
- **Entity**: `sensor.{climate_name}_seasonal_adaptation`
- **Description**: Seasonal learning system status
- **Values**: `Unknown` / `Enabled` / `Disabled`
- **Example**: `Unknown`
- **Note**: Requires outdoor sensor and AC cycles

### Seasonal Contribution
- **Entity**: `sensor.{climate_name}_seasonal_contribution`
- **Unit**: %
- **Description**: How much seasonal patterns affect predictions
- **Range**: 0-100%
- **Example**: `0.0%`
- **Note**: Increases as seasonal patterns are learned

### Weather Forecast
- **Entity**: `sensor.{climate_name}_weather_forecast`
- **Description**: Weather-based prediction status
- **Values**: `Unknown` / `Available` / `Not Available`
- **Example**: `Unknown`
- **Note**: Requires weather entity configuration

---

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
- Persistence Latency: <100ms

### Warning Signs
- Accuracy dropping below 50%
- Cycle Health: 1 or 2 (short cycling)
- Average cycles: <7 minutes
- Outlier Count: Increasing rapidly
- Sensor Availability: <100%

---

## Sensor Update Frequencies

- **Real-time** (every coordinator update): Current values, offsets, temperatures
- **Every 5 minutes**: Learning samples, ML metrics
- **Every 60 minutes**: Persistence, seasonal data
- **On AC state change**: Hysteresis, cycles, thermal state
- **Daily**: Thermal probing (during calibration window)

---

## Using Sensors for Automation

Example automations using these sensors:

```yaml
# Alert on poor accuracy
automation:
  - alias: "Climate Learning Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.climate_current_accuracy
        below: 50
        for: "01:00:00"
    action:
      - service: notify.mobile
        data:
          message: "Climate learning accuracy low: {{ states('sensor.climate_current_accuracy') }}%"

# Detect short cycling
automation:
  - alias: "AC Short Cycling Alert"
    trigger:
      - platform: state
        entity_id: sensor.climate_cycle_health
        to: "1"
    action:
      - service: notify.mobile
        data:
          message: "Warning: AC is short cycling"
```

---

## Glossary

- **Tau (τ)**: Time constant - how fast a room heats/cools
- **Hysteresis**: The lag between cause and effect in AC cycles
- **PRIMING**: Initial conservative learning state
- **Offset**: Temperature compensation applied to AC setpoint
- **Correlation**: Statistical relationship between variables
- **R-Squared**: Proportion of variance explained by the model
- **EMA**: Exponential Moving Average - weighted average favoring recent data
- **MAE**: Mean Absolute Error - average prediction error
- **Outlier**: Data point significantly different from others
- **Short Cycling**: AC turning on/off too frequently (<7 min cycles)