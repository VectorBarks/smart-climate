# Advanced Configuration and Technical Guide

This guide provides in-depth technical information for advanced users who want to understand and optimize Smart Climate Control's behavior.

## Architecture Overview

### Component Hierarchy
```
SmartClimateEntity (climate.py)
├── OffsetEngine (offset_engine.py) - Core offset calculations
├── SensorManager (sensor_manager.py) - Sensor state management  
├── ModeManager (mode_manager.py) - Operating mode logic
├── TemperatureController (temperature_controller.py) - Command handling
├── DelayLearner (delay_learner.py) - v1.3.0 Adaptive delays
├── ForecastEngine (forecast_engine.py) - v1.3.0 Weather predictions
└── SeasonalLearner (seasonal_learner.py) - v1.3.0 Seasonal adaptation
```

### Data Flow
1. **Sensor Updates** → SensorManager → Coordinator → Entity refresh
2. **Temperature Commands** → Entity → TemperatureController → Wrapped entity
3. **Learning Feedback** → OffsetEngine → LightweightLearner → Data persistence
4. **Mode Changes** → ModeManager → Offset recalculation → Temperature adjustment

## v1.3.0 Advanced Features Deep Dive

### Adaptive Feedback Delays Technical Details

#### Algorithm Implementation
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

#### Constants and Tuning
```python
STABILITY_THRESHOLD = 0.1  # °C - Temperature change for stability detection
CHECK_INTERVAL = 15        # seconds - Temperature monitoring frequency  
LEARNING_TIMEOUT = 10      # minutes - Maximum learning cycle duration
EMA_ALPHA = 0.3           # Smoothing factor (30% new, 70% old)
SAFETY_BUFFER_SECS = 5    # Added to all learned delays
```

#### Performance Characteristics
- **Memory Usage**: ~1KB per climate entity for delay history
- **CPU Impact**: Negligible (<0.1ms per temperature check)
- **Storage**: Uses Home Assistant Store API (JSON persistence)
- **Learning Rate**: Typically converges within 5-10 HVAC cycles

#### Debugging Adaptive Delays
Enable debug logging to monitor learning cycles:
```yaml
logger:
  default: info
  logs:
    custom_components.smart_climate.delay_learner: debug
```

Debug output examples:
```
[DEBUG] DelayLearner: Starting learning cycle for climate.living_room_ac
[DEBUG] DelayLearner: Temperature stabilized after 47 seconds
[DEBUG] DelayLearner: Updated learned delay: 45s → 48s (EMA applied)
[DEBUG] DelayLearner: Learning cycle completed, next delay: 48s
```

### Weather Forecast Integration Technical Details

#### API Integration
```python
# Forecast fetching via Home Assistant weather service
forecast_data = await self._hass.services.async_call(
    "weather", "get_forecasts",
    {"entity_id": self._weather_entity, "type": "hourly"},
    blocking=True, return_response=True
)
```

#### Strategy Evaluation Engine
```python
def _evaluate_heat_wave_strategy(self, config: Dict[str, Any], now: datetime) -> None:
    trigger_temp = config.get("trigger_temp", 30.0)
    trigger_duration = config.get("trigger_duration", 3)
    
    # Find consecutive hours above threshold
    consecutive_hot_hours = 0
    for forecast in self._forecast_data:
        if forecast.temperature >= trigger_temp:
            consecutive_hot_hours += 1
            if consecutive_hot_hours >= trigger_duration:
                # Activate strategy
                self._activate_strategy(config)
                break
        else:
            consecutive_hot_hours = 0
```

#### Offset Combination Logic
```python
# In SmartClimateEntity._calculate_target_temperature()
reactive_offset = self._offset_engine.calculate_offset(input_data).offset
predictive_offset = self._forecast_engine.predictive_offset
total_offset = reactive_offset + predictive_offset

# Apply safety limits
total_offset = max(min(total_offset, self._max_offset), -self._max_offset)
```

#### Performance and Rate Limiting
- **Throttling**: 30-minute minimum between forecast fetches
- **Cache Duration**: Forecast data cached for efficiency
- **API Calls**: Minimal - only when needed and throttled
- **Fallback Behavior**: Graceful degradation when weather service unavailable

#### Custom Strategy Development
Create custom weather strategies by extending the configuration:
```yaml
forecast_strategies:
  - type: "morning_preheat"      # Custom strategy name
    enabled: true
    trigger_temp: 15.0           # Below 15°C
    trigger_duration: 2          # For 2+ hours
    adjustment: 2.0              # Positive for pre-heating
    max_duration: 3              # Active for 3 hours max
    time_range: [5, 10]          # Only active 5:00-10:00 AM
    conditions: ["clear", "sunny"] # Only on clear mornings
```

### Seasonal Adaptation Technical Details

#### Temperature Bucket Algorithm
```python
def _find_patterns_by_outdoor_temp(
    self, target_temp: float, tolerance: float
) -> List[LearnedPattern]:
    """Find patterns within temperature tolerance."""
    return [
        pattern for pattern in self._patterns
        if abs(pattern.outdoor_temp - target_temp) <= tolerance
    ]

def get_relevant_hysteresis_delta(
    self, current_outdoor_temp: Optional[float] = None
) -> Optional[float]:
    """Calculate relevant delta using bucket approach."""
    if current_outdoor_temp is None:
        current_outdoor_temp = self._get_current_outdoor_temp()
    
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

#### Data Structure and Persistence
```python
@dataclass
class LearnedPattern:
    timestamp: float      # Unix timestamp
    start_temp: float     # AC start temperature
    stop_temp: float      # AC stop temperature  
    outdoor_temp: float   # Outdoor temperature context
    
    @property
    def hysteresis_delta(self) -> float:
        return self.start_temp - self.stop_temp
```

#### Storage Schema
```json
{
  "version": 1,
  "patterns": [
    {
      "timestamp": 1689234567.89,
      "start_temp": 24.5,
      "stop_temp": 22.1,
      "outdoor_temp": 31.2
    }
  ]
}
```

#### Pruning and Maintenance
- **Retention Period**: 45 days (configurable via `_data_retention_days`)
- **Automatic Pruning**: Runs on load and periodically during operation
- **Memory Management**: Efficient in-memory pattern storage
- **Performance**: O(n) pattern matching where n = patterns in bucket

## Performance Optimization

### Memory Usage Optimization
```python
# Efficient pattern storage
class SeasonalHysteresisLearner:
    def _prune_old_patterns(self) -> None:
        cutoff_time = time.time() - (self._data_retention_days * 24 * 3600)
        self._patterns = [p for p in self._patterns if p.timestamp > cutoff_time]
```

### Update Frequency Tuning
```yaml
# Balance accuracy vs. performance
update_interval: 120  # Faster updates = more responsive, higher CPU
save_interval: 30     # More frequent saves = better data protection, more I/O
```

### Sensor Update Requirements
- **Room Sensor**: Update every 1-2 minutes for optimal learning
- **Outdoor Sensor**: Update every 5-15 minutes sufficient for seasonal adaptation
- **Power Sensor**: Update every 10-60 seconds for accurate state detection
- **Weather Entity**: Hourly updates sufficient for forecast integration

## Advanced Configuration Patterns

### Multi-Zone Optimization
```yaml
smart_climate:
  # Main zone with all features
  - name: "Main Zone"
    climate_entity: climate.main_ac
    room_sensor: sensor.main_temp
    outdoor_sensor: sensor.outdoor_temp
    power_sensor: sensor.main_ac_power
    weather_entity: weather.home
    adaptive_delay: true
    seasonal_learning: true
    update_interval: 120
    
  # Secondary zones share outdoor sensor
  - name: "Bedroom Zone"
    climate_entity: climate.bedroom_ac  
    room_sensor: sensor.bedroom_temp
    # outdoor_sensor inherited from first entity
    adaptive_delay: true
    gradual_adjustment_rate: 0.2  # Gentler for sleeping
    
  # Guest zone minimal features
  - name: "Guest Zone"
    climate_entity: climate.guest_ac
    room_sensor: sensor.guest_temp
    update_interval: 300  # Less frequent updates
    away_temperature: 28  # Higher default for unoccupied
```

### Climate-Specific Optimization
```yaml
# High-efficiency inverter AC
- name: "Inverter AC"
  adaptive_delay: true
  gradual_adjustment_rate: 0.2  # Small adjustments work best
  learning_feedback_delay: 30   # Fast response time
  power_idle_threshold: 20      # Low idle power
  
# Older standard AC
- name: "Standard AC"  
  gradual_adjustment_rate: 0.8  # Larger adjustments needed
  learning_feedback_delay: 90   # Slower response
  power_idle_threshold: 100     # Higher idle power
  
# Central air system  
- name: "Central AC"
  gradual_adjustment_rate: 0.3  # Moderate adjustments
  learning_feedback_delay: 120  # Very slow response
  update_interval: 300          # Less frequent updates for large systems
```

### Environmental Optimization
```yaml
# Hot climate optimization
- name: "Desert Climate AC"
  weather_entity: weather.home
  forecast_strategies:
    - type: "heat_wave"
      trigger_temp: 35.0      # Higher threshold for desert
      trigger_duration: 4     # Longer duration required  
      adjustment: -2.0        # Aggressive pre-cooling
      max_duration: 10        # Extended strategy duration
      
# Humid climate optimization  
- name: "Humid Climate AC"
  boost_offset: -1.0          # Less aggressive boost (dehumidification priority)
  gradual_adjustment_rate: 0.3 # Gentler for humidity control
  
# Variable climate optimization
- name: "Variable Climate AC"
  seasonal_learning: true     # Essential for changing conditions
  adaptive_delay: true        # Adapt to seasonal AC behavior changes
  data_retention_days: 90     # Longer retention for seasonal patterns
```

## Debug and Monitoring

### Comprehensive Debug Logging
```yaml
logger:
  default: info
  logs:
    # Core components
    custom_components.smart_climate: debug
    custom_components.smart_climate.offset_engine: debug
    custom_components.smart_climate.climate: debug
    
    # v1.3.0 features
    custom_components.smart_climate.delay_learner: debug
    custom_components.smart_climate.forecast_engine: debug
    custom_components.smart_climate.seasonal_learner: debug
    
    # Data persistence
    custom_components.smart_climate.data_store: debug
    custom_components.smart_climate.lightweight_learner: debug
```

### Performance Monitoring
Enable timing logs to monitor performance:
```yaml
logger:
  logs:
    custom_components.smart_climate.coordinator: debug
```

Look for timing information in logs:
```
[DEBUG] SmartClimateCoordinator: Update completed in 2.3ms
[DEBUG] OffsetEngine: Calculation completed in 0.8ms  
[DEBUG] DelayLearner: Temperature check completed in 0.1ms
```

### Entity Attribute Monitoring
Monitor these attributes for system health:
```python
# Climate entity attributes
state.attributes.get('confidence_level')      # Learning quality
state.attributes.get('sample_count')          # Learning progress
state.attributes.get('calibration_status')    # Current phase
state.attributes.get('save_count')            # Data persistence health
state.attributes.get('adaptive_delay_learned') # Delay optimization
state.attributes.get('forecast_active_strategy') # Weather strategy status
state.attributes.get('seasonal_patterns_count')  # Seasonal learning progress
```

## Troubleshooting Advanced Features

### Adaptive Delays Not Learning
1. **Check HVAC Mode Changes**: Learning only triggers on mode changes
2. **Verify Temperature Sensor Updates**: Need frequent updates (every 1-2 minutes)
3. **Monitor Learning Cycles**: Enable debug logging to see cycle start/end
4. **Check Stability Threshold**: Very stable environments may need lower threshold

### Weather Integration Issues
1. **Verify Weather Entity**: Must provide `weather.get_forecasts` service
2. **Check Forecast Data**: Developer Tools → Services → Test weather.get_forecasts
3. **Monitor API Throttling**: 30-minute minimum between forecast fetches
4. **Strategy Configuration**: Verify trigger conditions are achievable

### Seasonal Learning Problems
1. **Outdoor Sensor Validation**: Must provide numeric temperature values
2. **Data Collection**: Requires outdoor sensor updates during AC operation
3. **Bucket Population**: Need 3+ samples per temperature bucket (5°C ranges)
4. **Retention Period**: Ensure sufficient data retention (45+ days recommended)

## Migration and Upgrade Notes

### Upgrading from v1.2.x to v1.3.0
- **New features disabled by default**: Existing installations unchanged
- **Storage schema**: Automatically upgraded with backward compatibility
- **Configuration**: No breaking changes, all new options are optional
- **Performance**: Minimal impact with features disabled

### Data Migration
```python
# Storage schema versioning handles migration automatically
# Old data preserved and enhanced with new fields as needed
# No manual migration required
```

## API Reference for Developers

### Custom Strategy Development
Extend forecast strategies by implementing the evaluation pattern:
```python
def _evaluate_custom_strategy(self, config: Dict[str, Any], now: datetime) -> None:
    """Implement custom strategy evaluation logic."""
    # Parse configuration
    trigger_condition = config.get("trigger_condition")
    
    # Evaluate against forecast data
    if self._check_forecast_condition(trigger_condition):
        # Activate strategy
        strategy = ActiveStrategy(
            name=config.get("type"),
            adjustment=config.get("adjustment", 0.0),
            end_time=now + timedelta(hours=config.get("max_duration", 1))
        )
        self._active_strategy = strategy
```

### Storage API Usage
```python
# Custom storage for additional data
from homeassistant.helpers.storage import Store

store = Store(hass, version=1, key="smart_climate_custom_data")
data = await store.async_load() or {}
data["custom_field"] = "custom_value"  
await store.async_save(data)
```

This advanced guide provides the technical depth needed for optimizing Smart Climate Control's v1.3.0 features. For basic setup, see the [Configuration Guide](configuration.md). For troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).