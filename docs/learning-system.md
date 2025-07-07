# Learning System Documentation

This document provides a detailed explanation of Smart Climate Control's intelligent learning system and feedback mechanism.

## Overview

The learning system uses a lightweight, efficient approach to continuously improve temperature offset predictions by learning from your specific AC unit and environment. Unlike heavy machine learning solutions, this system is designed to run efficiently on Home Assistant with minimal resource usage.

## Core Concepts

### What the System Learns

The learning system identifies patterns in:
- **Sensor Offset Variations**: How the difference between AC and room sensors changes
- **Time-of-Day Effects**: Daily temperature patterns and usage
- **Environmental Correlations**: How outdoor temperature affects indoor control
- **Power State Patterns**: When the AC is actually cooling vs idle (if power sensor available)
- **Mode-Specific Behaviors**: Different patterns for sleep, away, and boost modes

### How Learning Works

1. **Pattern Recognition**: Uses exponential smoothing to identify recurring patterns
2. **Incremental Updates**: Learns from each temperature adjustment without storing massive datasets
3. **Confidence Scoring**: Tracks how reliable predictions are for different conditions
4. **Adaptive Weighting**: Balances learned predictions with rule-based calculations

## The Feedback Mechanism

### Understanding Feedback Collection

The feedback mechanism is the key to continuous improvement. Here's exactly what happens:

#### Step 1: Offset Prediction (T=0 seconds)
When you adjust the temperature:
```
User sets: 22°C
Current room temp: 24°C
AC internal sensor: 23.5°C
System predicts: +2°C offset needed
Sends to AC: 20°C
```

#### Step 2: Stabilization Period (T=0 to 45 seconds)
The AC unit responds to the new setpoint:
- Internal temperature sensor begins changing
- Compressor may start/stop
- Air temperature at vents changes
- Internal sensor reading stabilizes

#### Step 3: Feedback Collection (T=45 seconds default)
The system measures actual performance:
```
AC internal sensor now: 21°C
Room sensor still: 24°C
Actual offset: 24 - 21 = 3°C
Prediction error: 3 - 2 = 1°C
```

#### Step 4: Learning Update
The system updates its patterns:
- Records the prediction error
- Updates time-of-day pattern for current hour
- Adjusts environmental correlations
- Improves future predictions for similar conditions

### What Feedback Measures

**Important Understanding**: The feedback mechanism does NOT measure:
- Whether the room reached target temperature (NOT measured)
- How long it takes to cool/heat the room (NOT measured)
- The AC's cooling efficiency (NOT measured)

Instead, it measures:
- The actual sensor offset after stabilization
- How accurate the prediction was
- Patterns in prediction errors
- Environmental factors affecting offsets

### Configuring Feedback Timing

The `learning_feedback_delay` parameter is crucial for accurate learning:

```yaml
smart_climate:
  - name: "Living Room AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    learning_feedback_delay: 45  # Default: 45 seconds
```

#### Determining Optimal Delay

Different AC types require different delays:

**Fast-responding units (30-60 seconds)**:
- Modern inverter mini-splits
- Small room units
- Systems with electronic controls

**Standard units (45-90 seconds)**:
- Typical central AC systems
- Standard split systems
- Most heat pumps

**Slow-responding units (90-180 seconds)**:
- Older systems with mechanical controls
- Large commercial-style units
- Systems with long duct runs

#### How to Find Your Optimal Setting

1. Enable debug logging:
   ```yaml
   logger:
     logs:
       custom_components.smart_climate: debug
   ```

2. Make a temperature adjustment and watch the logs

3. Look for sensor stabilization:
   ```
   DEBUG: AC internal temperature: 23.5°C
   DEBUG: AC internal temperature: 23.2°C
   DEBUG: AC internal temperature: 22.8°C
   DEBUG: AC internal temperature: 21.5°C
   DEBUG: AC internal temperature: 21.2°C
   DEBUG: AC internal temperature: 21.0°C  # Stabilized
   ```

4. Set feedback delay 10-15 seconds after typical stabilization

## Learning Algorithm Details

### Exponential Smoothing

The system uses exponential smoothing for pattern learning:
- Recent observations weighted more heavily
- Older patterns gradually fade
- Prevents overfitting to anomalies
- Maintains long-term stability

### Pattern Storage

Learned patterns include:
```python
{
  "time_patterns": {
    "00": {"offset_avg": 1.8, "confidence": 0.7},
    "01": {"offset_avg": 1.6, "confidence": 0.7},
    ...
    "23": {"offset_avg": 2.0, "confidence": 0.8}
  },
  "temp_correlation": {
    "slope": 0.05,
    "intercept": 1.5
  },
  "power_patterns": {
    "on_offset": 2.5,
    "off_offset": 0.8
  }
}
```

### Confidence Scoring

Confidence increases with:
- More samples collected
- Consistent predictions
- Low prediction errors
- Stable environmental conditions

Confidence decreases with:
- High prediction variability
- Environmental changes
- System modifications
- Sensor issues

## Data Collection Quality

### When Feedback is Collected

The system only collects feedback when:
- An offset was actually applied (not zero)
- All required sensors are available
- The system is in a learning-enabled mode
- The feedback delay has elapsed
- The entity still exists (not removed)

### When Feedback is Skipped

Feedback collection is skipped when:
- Learning is disabled via the switch
- Sensors become unavailable
- The AC is turned off
- Manual override is active
- Entity is being removed

### Data Validation

The system validates data quality:
- Outlier detection for anomalous readings
- Sensor sanity checks (reasonable temperature ranges)
- Consistency validation between readings
- Minimum change thresholds

## Performance Characteristics

### Resource Usage
- **Memory**: <1MB for pattern storage
- **CPU**: <1ms per prediction
- **Storage**: ~50KB per climate entity
- **Network**: No external connections

### Learning Speed
- **Initial Patterns**: 24-48 hours
- **Basic Accuracy**: 3-5 days
- **Optimal Performance**: 2-4 weeks
- **Seasonal Adaptation**: 1-2 months

### Accuracy Metrics

Typical accuracy progression:
- Day 1: 60-70% accuracy
- Week 1: 75-85% accuracy
- Month 1: 85-95% accuracy
- Ongoing: 90-95% maintained

## Monitoring Learning Performance

### Debug Logging

Enable detailed logging to monitor learning:

```yaml
logger:
  default: info
  logs:
    custom_components.smart_climate: debug
    custom_components.smart_climate.offset_engine: debug
    custom_components.smart_climate.lightweight_learner: debug
```

Key log messages to watch:
```
DEBUG: Learning feedback collected: predicted_offset=2.00°C, actual_offset=2.30°C, error=0.30°C
INFO: Learning patterns updated: samples=156, accuracy=0.89, confidence=0.75
DEBUG: Pattern learning: time_pattern_updated=14:00, new_avg=2.15°C
```

### Learning Metrics

Monitor through the learning switch attributes:

```yaml
switch.living_room_ac_learning:
  learning_enabled: true
  samples_collected: 245
  learning_accuracy: 0.91
  confidence_level: 0.82
  last_update: "2024-01-15 14:30:00"
  average_error: 0.25
  prediction_quality: "excellent"
  patterns_detected:
    - "morning_warmup"
    - "afternoon_peak"
    - "evening_stable"
```

### Performance Indicators

Good learning performance shows:
- Steadily increasing sample count
- Improving accuracy over time
- Growing confidence levels
- Decreasing average error
- Consistent pattern detection

## Advanced Topics

### Pattern Types

#### Time-of-Day Patterns
- 24-hour cycle tracking
- Hourly offset averages
- Confidence per time slot
- Smooth transitions between hours

#### Environmental Correlations
- Outdoor temperature impact
- Linear regression modeling
- Adaptive correlation strength
- Seasonal adjustments

#### Power-Based Patterns
- Active cooling detection
- Idle state recognition
- Cycle timing patterns
- Energy efficiency tracking

### Learning Rate Adaptation

The system adjusts learning rates based on:
- Pattern stability
- Environmental changes
- Prediction accuracy
- Time since last update

### Multi-Mode Learning

Different operating modes can have distinct patterns:
- Normal mode: Standard patterns
- Sleep mode: Night-specific adjustments
- Away mode: Minimal learning
- Boost mode: Temporary patterns not learned

## Troubleshooting Learning Issues

### Poor Prediction Accuracy

If accuracy remains low:
1. Verify sensor placement and accuracy
2. Check for environmental disturbances
3. Ensure consistent AC operation
4. Review feedback delay setting
5. Look for patterns in debug logs

### Slow Learning

If patterns develop slowly:
1. Ensure learning is enabled consistently
2. Check sample collection rate
3. Verify feedback is being collected
4. Consider environmental stability
5. Review sensor reliability

### Erratic Predictions

If predictions vary wildly:
1. Check for sensor issues
2. Look for environmental changes
3. Verify AC unit consistency
4. Review recent manual overrides
5. Consider resetting learning data

## Future Enhancements

### Planned Improvements

**Adaptive Feedback Timing**
- Automatic delay adjustment
- Stability detection algorithms
- Multi-point sampling
- Dynamic collection intervals

**Advanced Pattern Recognition**
- Seasonal pattern separation
- Weather forecast integration
- Occupancy-based patterns
- Multi-zone coordination

**Enhanced Learning**
- Deep learning for complex patterns
- Anomaly detection and filtering
- Predictive adjustments
- Energy optimization goals

### Research Areas

- Neural network integration (optional module)
- Federated learning for community benefits
- Predictive maintenance indicators
- Advanced visualization tools

## Conclusion

The Smart Climate Control learning system provides intelligent, adaptive climate control while remaining lightweight and efficient. By understanding how the feedback mechanism works and properly configuring your system, you can achieve optimal comfort with minimal energy usage.

For specific configuration options, see the [Configuration Guide](configuration.md).
For troubleshooting help, see the [Troubleshooting Guide](troubleshooting.md).