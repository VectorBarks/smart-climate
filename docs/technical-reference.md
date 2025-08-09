# Technical Reference

This comprehensive technical reference covers Smart Climate Control's architecture, algorithms, advanced features, and troubleshooting guidance.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Thermal Efficiency Management](#thermal-efficiency-management)
3. [AC Temperature Window Detection](#ac-temperature-window-detection-hysteresislearner)
4. [Weather Forecast Integration](#weather-forecast-integration)
5. [Confidence Calculation System](#confidence-calculation-system)
6. [Advanced Configuration](#advanced-configuration-and-optimization)
7. [Performance Characteristics](#performance-characteristics)
8. [Troubleshooting Guide](#troubleshooting-guide)

## Architecture Overview

### Core Design Principles

Smart Climate Control follows a modular, fail-safe architecture emphasizing reliability, testability, and maintainability.

#### Separation of Concerns
Each component has a single, well-defined responsibility:
- **Climate Entity**: User interface and Home Assistant integration
- **Offset Engine**: Temperature offset calculations and learning
- **Sensor Manager**: Sensor reading and availability monitoring
- **Mode Manager**: Operating mode logic and adjustments
- **Temperature Controller**: Command execution and safety limits
- **Data Store**: Persistence and data management

#### Dependency Injection
All components use constructor-based dependency injection:
- Improves testability through easy mocking
- Reduces coupling between components
- Makes dependencies explicit and manageable
- Enables flexible configuration

#### Fail-Safe Design
The system continues operating even when components fail:
- Missing sensors trigger graceful degradation
- Learning failures don't affect basic operation
- Persistence errors don't crash the system
- Network issues are handled transparently

### Component Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  Home Assistant │────▶│ SmartClimateEntity│
└─────────────────┘     └──────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌──────────────┐ ┌──────────────┐ ┌────────────────┐
        │SensorManager │ │ OffsetEngine │ │ ModeManager    │
        └──────────────┘ └──────┬───────┘ └────────────────┘
                               │
                        ┌──────▼────────┐
                        │ Lightweight   │
                        │ Learner       │
                        └──────┬────────┘
                               │
                        ┌──────▼────────┐
                        │  DataStore    │
                        └───────────────┘
```

### Core Components

#### SmartClimateEntity
- Implements Home Assistant ClimateEntity interface
- Forwards commands to wrapped climate entity
- Applies calculated offsets to temperature commands
- Exposes current room temperature from sensors
- Manages preset modes and manual overrides

#### OffsetEngine
- Rule-based offset calculations
- Integration with learning system
- Confidence scoring for predictions
- Safety limit enforcement
- Performance feedback recording

**Key Algorithms**:
- Base offset: `room_temp - ac_internal_temp`
- Mode adjustments applied additively
- Learning predictions weighted by confidence
- Gradual adjustments to prevent oscillation

#### LightweightOffsetLearner
- <1ms prediction time requirement
- <1MB memory usage limit
- Incremental learning approach
- No external dependencies
- Graceful degradation without historical data

**Design Features**:
- Time-of-day pattern recognition
- Environmental correlation learning
- Exponential smoothing for stability
- Confidence scoring for predictions
- JSON serialization for persistence

### Data Flow

#### Temperature Setting Flow
1. User sets desired temperature (22°C)
2. SmartClimateEntity receives command
3. Coordinator provides current sensor data
4. OffsetEngine calculates required offset
5. TemperatureController applies offset and limits
6. Command sent to wrapped entity (20°C)
7. Feedback collected after delay
8. Learning system updates patterns

#### Learning Feedback Flow
1. Temperature adjustment made
2. Timer started for feedback delay
3. After delay, current offset measured
4. Comparison with prediction made
5. Error calculated and recorded
6. Learning patterns updated
7. Confidence scores adjusted
8. Data persisted to storage

## Thermal Efficiency Management

The Thermal Efficiency system optimizes AC operation through learning room thermal characteristics and intelligent control decisions.

### Components

#### 1. Thermal Model
- **Purpose**: Learns room's thermal physics (cooling/warming time constants)
- **Key Metrics**: Tau values (τ_cooling, τ_warming)
- **Status**: Always enabled (required for other components)

#### 2. Thermal Preferences
- **Purpose**: Adapts comfort bands based on user preferences
- **Levels**: MAX_COMFORT → COMFORT_PRIORITY → BALANCED → SAVINGS_PRIORITY → MAX_SAVINGS
- **Default**: BALANCED

#### 3. Thermal Monitor
- **Purpose**: Tracks thermal behavior anomalies and efficiency metrics
- **Default**: Disabled (`monitor=False`)
- **Features**: Detects unusual rates, external disturbances, performance degradation

#### 4. Thermal Controller
- **Purpose**: Actively controls AC based on thermal predictions
- **Default**: Disabled (`controller=False` = shadow mode)
- **Shadow Mode**: Observes and learns without actively controlling

#### 5. Thermal Manager
- **Purpose**: Coordinates all thermal components
- **Status**: Always enabled when thermal efficiency is active

### Shadow Mode Operation

Shadow mode is the default during initial learning phases (`controller=False`).

**What Shadow Mode Does**:
- **Observes**: Watches your AC's actual behavior
- **Learns**: Builds thermal model without disruption
- **Calculates**: Determines what it WOULD do if in control
- **Reports**: Shows decisions via sensors
- **Does NOT Control**: AC operates normally without intervention

**Why Shadow Mode Exists**:
1. **Safe Learning**: Avoids disrupting comfort during setup
2. **Validation**: Allows verification of decisions before enabling control
3. **Gradual Transition**: Builds confidence before taking control

### Thermal States

The system operates in six distinct states:

#### 1. PRIMING (Initial 24-48 hours)
- Conservative learning phase
- Minimal offsets (±0.1-0.2°C)
- Tight temperature windows
- Conservative tau values (1.5/2.5 minutes)
- Shadow mode enabled

#### 2. DRIFTING
- AC off, temperature naturally drifting
- Monitors natural temperature change
- Refines tau_warming value

#### 3. CORRECTING
- AC actively cooling/heating
- Monitors active temperature correction
- Refines tau_cooling value

#### 4. RECOVERY
- Recovering from mode changes
- Triggered after switching heat/cool modes
- Duration: 15-30 minutes

#### 5. PROBING
- Active thermal characteristic learning
- Controlled on/off cycles to measure response
- Daily during calibration window (default: 2-6 AM)

#### 6. CALIBRATING
- Fine-tuning offset predictions
- Triggered after sufficient data collection
- Results in optimized control parameters

### Thermal Decision Making

The thermal manager considers:
1. **Current Temperature**: Within comfort bounds?
2. **Temperature Trend**: Moving toward or away from target?
3. **Thermal Momentum**: Will it overshoot if AC continues?
4. **Efficiency**: Can we coast to target without AC?
5. **Comfort Preference**: How tight should control be?

### Tau Value Interpretation

**Tau Cooling** (τc):
- Time for room to cool 63% toward AC setpoint
- Typical values: 60-120 minutes
- Lower = room cools faster
- Affected by: AC power, room size, insulation

**Tau Warming** (τw):
- Time for room to warm 63% toward ambient
- Typical values: 90-180 minutes
- Higher = room holds temperature longer
- Affected by: Insulation, external heat sources

## AC Temperature Window Detection (HysteresisLearner)

The HysteresisLearner system learns AC cooling cycle behavior for enhanced prediction accuracy.

### What is AC Hysteresis?

AC units cycle on/off based on internal temperature thresholds:
- **Start Cooling**: When temperature rises above threshold (e.g., 24.5°C for 24°C target)
- **Stop Cooling**: When temperature drops below different threshold (e.g., 23.5°C)
- **Hysteresis Window**: Temperature range between start/stop points (1°C in example)

### How HysteresisLearner Works

#### 1. Power Transition Detection
- Monitors AC power consumption to detect cooling start/stop
- **Cooling Start**: Power increases from idle/low to moderate/high
- **Cooling Stop**: Power decreases from moderate/high to idle/low
- Records room temperature at transition moments

#### 2. Threshold Learning
- Collects room temperature samples during power transitions
- Calculates median values for robust learning
- **Start Threshold**: Median room temperature when AC begins cooling
- **Stop Threshold**: Median room temperature when AC stops cooling

#### 3. Hysteresis State Detection
Based on learned thresholds and current conditions:
- **`learning_hysteresis`**: Insufficient data for thresholds
- **`active_phase`**: AC actively cooling (high power)
- **`idle_above_start_threshold`**: AC off, temp above start point
- **`idle_below_stop_threshold`**: AC off, temp below stop point
- **`idle_stable_zone`**: AC off, temp between thresholds

#### 4. Enhanced Predictions
- Factors hysteresis state into offset predictions
- Different states yield different prediction patterns
- Improves learning accuracy through AC cycle context

### Requirements

**Essential**:
- Power sensor monitoring AC electrical consumption
- Home Assistant climate entity
- Room temperature sensor

**Power Sensor Types**:
- Smart plugs with power monitoring
- Whole-home energy monitors with CT clamps
- Built-in power reporting (some smart AC units)
- Dedicated power meters

**Without Power Sensor**: HysteresisLearner automatically disables, system continues with existing methods.

### Understanding Internal Sensor Thermal Dynamics

Many internal AC sensors show behavior perfect for HysteresisLearner:

**During Active Cooling**:
- Internal fan runs, mixing warm room air with cold evaporator
- Sensor reads averaged temperature (matches target)

**After Cooling Stops**:
- Fans stop, no airflow mixing
- Sensor reads pure evaporator coil temperature
- Temperature drops significantly (4-5°C difference typical)

**Why This Happens**:
- Evaporator coil has thermal mass, stays cold after compressor stops
- Without airflow, sensor measures actual coil temperature
- Coil gradually warms toward room temperature over 10-30 minutes

**Perfect for Learning**:
- **Clear Transitions**: 4-5°C difference makes state detection trivial
- **Reliable Patterns**: Consistent behavior enables robust learning
- **Enhanced Accuracy**: System quickly learns AC's cooling cycle

### Performance Characteristics
- **Prediction Time**: <0.0001s (well under 1ms requirement)
- **Memory Usage**: Bounded by max_samples configuration
- **Learning Accuracy**: Improves over 5-10 cooling cycles
- **Learning Parameters**: 5 minimum samples, 50 maximum samples, median calculation

## Weather Forecast Integration

Smart Climate includes weather-based pre-cooling strategies for predictive temperature management.

### Key Concept: Pre-cooling Behavior

**Important**: Weather strategies are for **pre-cooling only**. They activate BEFORE weather events and expire when events BEGIN, not when they end.

#### Timeline Example
```
8:00 AM  - Heat wave detected for noon
         - Pre-cooling starts: Target 24°C → 22°C
         
12:00 PM - Heat wave period begins
         - Strategy expires
         - Target returns to 24°C
         - Building has pre-cooled thermal mass
         
6:00 PM  - Heat wave continues (no special offset)
         - Normal operation with tighter comfort bands
```

### Available Strategies

#### Heat Wave Strategy
- **Purpose**: Pre-cool building thermal mass before extreme heat
- **Default Trigger**: >30°C
- **Configuration**:
  - `heat_wave_temp_threshold`: Temperature trigger (20-40°C)
  - `heat_wave_min_duration_hours`: Minimum high temp duration (1-24h)
  - `heat_wave_lookahead_hours`: Forecast check period (1-72h)
  - `heat_wave_pre_action_hours`: Pre-cooling lead time (1-12h)
  - `heat_wave_adjustment`: Temperature offset (e.g., -2.0°C)

#### Clear Sky Strategy
- **Purpose**: Pre-cool before intense sun exposure
- **Configuration**:
  - `clear_sky_condition`: Weather condition (usually "sunny")
  - `clear_sky_min_duration_hours`: Minimum sunny period (1-24h)
  - `clear_sky_lookahead_hours`: Forecast check period (1-72h)
  - `clear_sky_pre_action_hours`: Pre-cooling lead time (1-12h)
  - `clear_sky_adjustment`: Temperature offset (e.g., -1.5°C)

### Strategy Behavior

#### Activation Rules
1. **First Match Wins**: Only ONE strategy active at a time
2. **Priority Order**: Evaluated in configuration order
3. **No Stacking**: Offsets don't combine (-2°C OR -1.5°C, never -3.5°C)

#### Mathematical Requirements
For strategies to work: `lookahead_hours >= pre_action_hours + min_duration_hours`

**Valid Example**:
```yaml
lookahead_hours: 12
min_duration_hours: 4
pre_action_hours: 2
# Can detect 4-hour events and pre-cool 2 hours before
```

### During Weather Events

After pre-cooling expires, comfort maintained by:
1. **Thermal Manager**: Automatically tightens comfort bands in extreme heat
2. **Building Thermal Mass**: Pre-cooled mass provides cooling inertia
3. **Regular ML Offsets**: Continue learning and adapting

### Technical Implementation

#### API Integration
```python
# Forecast fetching via Home Assistant weather service
forecast_data = await self._hass.services.async_call(
    "weather", "get_forecasts",
    {"entity_id": self._weather_entity, "type": "hourly"},
    blocking=True, return_response=True
)
```

#### Strategy Evaluation
```python
def _evaluate_heat_wave_strategy(self, config, now):
    trigger_temp = config.get("trigger_temp", 30.0)
    trigger_duration = config.get("trigger_duration", 3)
    
    # Find consecutive hours above threshold
    consecutive_hot_hours = 0
    for forecast in self._forecast_data:
        if forecast.temperature >= trigger_temp:
            consecutive_hot_hours += 1
            if consecutive_hot_hours >= trigger_duration:
                self._activate_strategy(config)
                break
        else:
            consecutive_hot_hours = 0
```

#### Offset Combination
```python
# Total offset combines reactive and predictive
reactive_offset = self._offset_engine.calculate_offset(input_data).offset
predictive_offset = self._forecast_engine.predictive_offset
total_offset = reactive_offset + predictive_offset

# Apply safety limits
total_offset = max(min(total_offset, self._max_offset), -self._max_offset)
```

### Performance and Rate Limiting
- **Throttling**: 30-minute minimum between forecast fetches
- **Cache Duration**: Forecast data cached for efficiency
- **API Calls**: Minimal, only when needed and throttled
- **Fallback**: Graceful degradation when weather unavailable

## Confidence Calculation System

Smart Climate uses a multi-factor confidence calculation that reflects actual learning maturity and prediction reliability.

### Problems with Previous Approach

The original confidence calculation:
- Started with base 0.5 confidence
- Added 0.2 for outdoor sensor, 0.2 for power sensor, 0.1 for special modes
- **Result**: Stuck at 0.5-0.7, never improved with learning

### New Multi-Factor Confidence Calculation

#### 1. Sample Count (Learning Maturity)
- **0-10 samples**: Very low confidence (0.0-0.2)
- **10-50 samples**: Low to moderate confidence (0.2-0.5)
- **50-200 samples**: Moderate to good confidence (0.5-0.8)
- **200+ samples**: High confidence potential (0.8-1.0)

Uses logarithmic curve reflecting diminishing returns.

#### 2. Condition Diversity
Tracks different operating conditions experienced:

**Temperature Ranges**: Different room/AC/outdoor temperature ranges
**Power States**: Idle, low, moderate, high power usage
**Operating Modes**: Normal, away, sleep, boost modes

**Confidence boost**: Up to +0.2 based on diversity

#### 3. Time Coverage
Tracks which hours have collected data:
- Morning (6 AM - 12 PM)
- Afternoon (12 PM - 6 PM)
- Evening (6 PM - 12 AM)  
- Night (12 AM - 6 AM)

**Confidence boost**: Up to +0.15 for comprehensive coverage

#### 4. Prediction Consistency
Tracks prediction accuracy:
- Closeness to actual required offsets
- Standard deviation of errors
- Trend of improving accuracy

**Confidence adjustment**: ±0.15 based on reliability

### Confidence Progression Phases

#### Phase 1: Initial Learning (0-20%)
- **Samples**: 0-10
- **Characteristics**: Just starting, high uncertainty, rule-based calculations
- **User Experience**: "Just starting to learn your AC's behavior"

#### Phase 2: Early Learning (20-40%)
- **Samples**: 10-50
- **Characteristics**: Basic patterns emerging, some time patterns
- **User Experience**: "Learning your daily patterns"

#### Phase 3: Moderate Confidence (40-60%)
- **Samples**: 50-150
- **Characteristics**: Solid patterns, multiple conditions, reliable predictions
- **User Experience**: "Understanding your AC's characteristics"

#### Phase 4: Good Confidence (60-80%)
- **Samples**: 150-300
- **Characteristics**: Comprehensive coverage, strong accuracy, handles edge cases
- **User Experience**: "Reliably optimizing your comfort"

#### Phase 5: High Confidence (80-100%)
- **Samples**: 300+
- **Characteristics**: Full seasonal patterns, excellent accuracy, optimal performance
- **User Experience**: "Fully optimized for your environment"

### Technical Implementation

```python
def calculate_multi_factor_confidence(stats, conditions, predictions):
    # Base confidence from sample count (0.0 to 0.5)
    sample_confidence = min(0.5, math.log(stats.samples + 1) / 10)
    
    # Diversity bonus (0.0 to 0.2)
    diversity_score = calculate_diversity(conditions)
    diversity_confidence = diversity_score * 0.2
    
    # Time coverage bonus (0.0 to 0.15)
    time_coverage = calculate_time_coverage(stats.hourly_data)
    time_confidence = time_coverage * 0.15
    
    # Prediction accuracy adjustment (-0.15 to +0.15)
    if predictions.available:
        accuracy_adjustment = (predictions.accuracy - 0.5) * 0.3
    else:
        accuracy_adjustment = 0.0
    
    # Combine all factors
    total_confidence = (
        sample_confidence +
        diversity_confidence +
        time_confidence +
        accuracy_adjustment
    )
    
    # Ensure bounds [0.0, 1.0]
    return max(0.0, min(1.0, total_confidence))
```

## Advanced Configuration and Optimization

### v1.3.0 Advanced Features

#### Adaptive Feedback Delays

**Algorithm Implementation**:
```python
# Exponential Moving Average with safety buffer
if self._learned_delay_secs is None:
    self._learned_delay_secs = measured_delay + SAFETY_BUFFER_SECS
else:
    # EMA: new_value = α * measurement + (1-α) * old_value
    self._learned_delay_secs = int(
        EMA_ALPHA * (measured_delay + SAFETY_BUFFER_SECS) + 
        (1 - EMA_ALPHA) * self._learned_delay_secs
    )
```

**Constants and Tuning**:
```python
STABILITY_THRESHOLD = 0.1  # °C - Temperature change for stability detection
CHECK_INTERVAL = 15        # seconds - Temperature monitoring frequency  
LEARNING_TIMEOUT = 10      # minutes - Maximum learning cycle duration
EMA_ALPHA = 0.3           # Smoothing factor (30% new, 70% old)
SAFETY_BUFFER_SECS = 5    # Added to all learned delays
```

#### Seasonal Adaptation Technical Details

**Temperature Bucket Algorithm**:
```python
def _find_patterns_by_outdoor_temp(self, target_temp, tolerance):
    """Find patterns within temperature tolerance."""
    return [
        pattern for pattern in self._patterns
        if abs(pattern.outdoor_temp - target_temp) <= tolerance
    ]

def get_relevant_hysteresis_delta(self, current_outdoor_temp=None):
    """Calculate relevant delta using bucket approach."""
    if current_outdoor_temp is None:
        return None
    
    # Find patterns in current temperature bucket (±2.5°C)
    bucket_tolerance = self._outdoor_temp_bucket_size / 2
    bucket_patterns = self._find_patterns_by_outdoor_temp(
        current_outdoor_temp, bucket_tolerance
    )
    
    if len(bucket_patterns) >= self._min_samples_for_bucket:
        # Use median of bucket patterns
        deltas = [p.hysteresis_delta for p in bucket_patterns]
        return statistics.median(deltas)
    
    # Fallback to all patterns if insufficient bucket data
    if self._patterns:
        all_deltas = [p.hysteresis_delta for p in self._patterns]
        return statistics.median(all_deltas)
    
    return None
```

**Data Structure**:
```python
@dataclass
class LearnedPattern:
    timestamp: float      # Unix timestamp
    start_temp: float     # AC start temperature
    stop_temp: float      # AC stop temperature  
    outdoor_temp: float   # Outdoor temperature context
    
    @property
    def hysteresis_delta(self):
        return self.start_temp - self.stop_temp
```

### Performance Optimization

#### Memory Usage
- **Pattern Storage**: Efficient in-memory with automatic pruning
- **Retention Period**: 45 days configurable
- **Performance**: O(n) pattern matching where n = patterns in bucket

#### Update Frequency Tuning
```yaml
# Balance accuracy vs. performance
update_interval: 120  # Faster = more responsive, higher CPU
save_interval: 30     # More frequent = better protection, more I/O
```

#### Sensor Requirements
- **Room Sensor**: 1-2 minute updates for optimal learning
- **Outdoor Sensor**: 5-15 minute updates sufficient
- **Power Sensor**: 10-60 second updates for state detection
- **Weather Entity**: Hourly updates sufficient

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
- **Day 1**: 60-70% accuracy
- **Week 1**: 75-85% accuracy
- **Month 1**: 85-95% accuracy
- **Ongoing**: 90-95% maintained

### Scalability
- Each climate entity independent
- Shared outdoor sensors supported  
- Learning data per-entity
- No inter-entity communication required

## Troubleshooting Guide

### Common Issues and Solutions

#### Learning System Issues

**Problem**: Poor prediction accuracy
**Symptoms**: Accuracy remains low after 2+ weeks
**Solutions**:
1. Verify sensor placement and accuracy
2. Check for environmental disturbances
3. Ensure consistent AC operation
4. Review feedback delay setting
5. Look for patterns in debug logs

**Problem**: Learning seems stuck
**Symptoms**: Sample count not increasing, last_sample_collected not updating
**Solutions**:
1. Verify learning switch is enabled
2. Check if temperature changes are occurring
3. Ensure sensors are working correctly
4. Review feedback delay appropriateness
5. Check debug logs for errors

#### Thermal Efficiency Issues

**Problem**: Shadow mode won't disable
**Solutions**:
1. Ensure PRIMING phase is complete (check thermal_state sensor)
2. Verify sufficient learning data exists
3. Check configuration for `controller: true`

**Problem**: Poor thermal predictions
**Solutions**:
1. Verify tau values are realistic (not default 1.5/2.5)
2. Check for external disturbances
3. Ensure consistent AC operation during learning
4. Enable thermal monitor for diagnostics

#### Weather Integration Issues

**Problem**: Weather strategies not activating
**Solutions**:
1. Check mathematical requirement: lookahead >= pre_action + min_duration
2. Verify weather entity provides forecast data
3. Ensure conditions match exactly ("sunny" not "clear")
4. Confirm thresholds achievable in your climate

**Problem**: Strategies deactivate unexpectedly
**Solutions**:
1. Remember strategies expire when weather event STARTS
2. Check only one strategy can be active at a time
3. Verify first matching strategy wins (check priority order)

#### Power Monitoring Issues

**Problem**: HysteresisLearner not learning
**Solutions**:
1. Verify power sensor working and updating
2. Check power thresholds match AC consumption patterns
3. Ensure AC actually cycles on/off
4. Allow 5-10 cooling cycles for initial learning

**Problem**: Inconsistent power state detection
**Solutions**:
1. Review and adjust power thresholds
2. Check thresholds have adequate gaps between them
3. Monitor power consumption during different AC states
4. Enable debug logging to see state transitions

### Debug Logging

Enable comprehensive debugging:

```yaml
logger:
  default: info
  logs:
    # Core components
    custom_components.smart_climate: debug
    custom_components.smart_climate.offset_engine: debug
    custom_components.smart_climate.climate: debug
    
    # Advanced features
    custom_components.smart_climate.delay_learner: debug
    custom_components.smart_climate.forecast_engine: debug
    custom_components.smart_climate.seasonal_learner: debug
    
    # Data persistence
    custom_components.smart_climate.data_store: debug
    custom_components.smart_climate.lightweight_learner: debug
```

### Performance Monitoring

Monitor system health through entity attributes:

```python
# Climate entity attributes for health monitoring
state.attributes.get('confidence_level')         # Learning quality
state.attributes.get('sample_count')             # Learning progress  
state.attributes.get('calibration_status')       # Current phase
state.attributes.get('save_count')               # Persistence health
state.attributes.get('adaptive_delay_learned')   # Delay optimization
state.attributes.get('forecast_active_strategy') # Weather strategy
state.attributes.get('seasonal_patterns_count')  # Seasonal learning
```

### System Health Indicators

**Healthy System**:
- Current Accuracy: >80%
- R-Squared: >0.7
- Correlation Coefficient: >0.7
- Cycle Health: 0
- Average cycles: >10 minutes
- Memory Usage: <100 KiB
- Persistence Latency: <100ms

**Warning Signs**:
- Accuracy dropping below 50%
- Cycle Health: 1 or 2 (short cycling)
- Average cycles: <7 minutes
- Outlier Count: Rapidly increasing
- Sensor Availability: <100%

### Migration and Compatibility

#### Version Upgrade Notes

**v1.4.1-beta5**:
- No breaking changes, fully backward compatible
- Removed obsolete seasonal migration code
- Enhanced shadow mode behavior

**v1.3.0**:
- New features disabled by default
- Storage schema automatically upgraded
- No breaking changes, all options optional

**Data Migration**: 
- Automatic storage schema versioning
- Old data preserved and enhanced
- No manual migration required

---

*Technical mastery of Smart Climate Control enables optimal comfort, efficiency, and system longevity.*