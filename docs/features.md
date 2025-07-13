# Smart Climate Control - Features Guide

This comprehensive guide covers all features available in Smart Climate Control, from basic temperature compensation to advanced learning and predictive capabilities.

## Core Features

### Universal Climate Entity Wrapping
Smart Climate Control works with **any** Home Assistant climate entity, making it universally compatible:
- Central air conditioning systems
- Mini-split/ductless units  
- Window units
- Heat pumps
- Any climate entity in Home Assistant

### Dynamic Temperature Offset Compensation
The core feature that addresses inaccurate internal sensors:
- **Real-time Offset Calculation**: Continuously calculates temperature differences between AC internal sensor and room sensor
- **Safety Limits**: Configurable maximum offset (default ±5°C) prevents extreme adjustments
- **Gradual Adjustments**: Configurable rate (0.1-2.0°C per cycle) prevents oscillation
- **Manual Overrides**: Users can always manually override learned adjustments

### Intelligent Learning System
Advanced machine learning capabilities that improve accuracy over time:
- **Lightweight ML Model**: <1ms prediction time with exponential smoothing
- **Pattern Recognition**: Learns time-of-day, temperature correlation, and usage patterns  
- **Hysteresis Learning**: Automatically detects AC on/off temperature thresholds
- **Confidence Tracking**: Multi-factor confidence calculation shows learning quality (0-100%)

## Advanced Features (v1.3.0)

### Adaptive Feedback Delays
*Automatically optimizes AC response timing based on actual hardware behavior*

**How It Works:**
- Monitors temperature changes every 15 seconds after HVAC mode changes
- Detects when temperature stabilizes (change < 0.1°C)
- Learns optimal delay timing using exponential moving average
- Applies 5-second safety buffer to learned delays

**Benefits:**
- Reduces energy waste from premature feedback
- Improves comfort accuracy by waiting for AC to reach equilibrium
- Adapts to different AC response characteristics automatically

**Configuration:**
```yaml
adaptive_delay: true  # Default: false (opt-in feature)
```

**Technical Details:**
- Uses Home Assistant Storage for persistence
- 10-minute timeout protection prevents endless learning cycles
- EMA smoothing factor: 0.3 (70% weight on new measurements)
- Triggers automatically on HVAC mode changes when enabled

### Weather Forecast Integration
*Proactive temperature adjustments based on upcoming weather conditions*

**How It Works:**
- Fetches weather forecasts using Home Assistant's weather integration
- Evaluates configurable strategies against forecast data
- Applies predictive offsets before weather conditions change
- Combines with reactive offsets: `total_offset = reactive_offset + predictive_offset`

**Built-in Strategies:**

#### Heat Wave Pre-cooling
Prepares for high temperatures by pre-cooling the space:
- **Trigger**: Forecast shows 30°C+ for 3+ consecutive hours
- **Action**: Applies -1.0°C offset to increase cooling
- **Duration**: Up to 8 hours maximum
- **Benefits**: More comfortable indoor climate during heat waves

#### Clear Sky Thermal Optimization  
Optimizes cooling efficiency during clear weather:
- **Trigger**: Clear or sunny conditions in forecast
- **Action**: Applies -0.5°C thermal optimization
- **Duration**: Up to 6 hours maximum  
- **Benefits**: Takes advantage of clear sky thermal dynamics

**Configuration:**
```yaml
weather_entity: "weather.home"
forecast_strategies:
  - type: "heat_wave"
    enabled: true
    trigger_temp: 30.0      # °C threshold
    trigger_duration: 3     # Hours required
    adjustment: -1.0        # Temperature offset
    max_duration: 8         # Maximum strategy duration
  - type: "clear_sky"
    enabled: true
    conditions: ["sunny", "clear"]
    adjustment: -0.5
    max_duration: 6
```

**Technical Details:**
- 30-minute internal throttling prevents excessive API calls
- Graceful degradation when weather service unavailable
- Complete forecast information exposed in entity attributes
- Strategy evaluation runs automatically every update cycle

### Seasonal Adaptation
*Context-aware learning that adapts to outdoor temperature patterns*

**How It Works:**
- Enhances hysteresis learning with outdoor temperature context
- Groups learned patterns by outdoor temperature ranges (5°C buckets)
- Retrieves relevant patterns based on current outdoor conditions
- Uses 45-day data retention to capture seasonal patterns

**Benefits:**
- Improved accuracy across different seasons
- Better performance during temperature transitions (spring/fall)
- Automatic adaptation to outdoor temperature influences
- More relevant pattern matching for current conditions

**Configuration:**
```yaml
outdoor_sensor: "sensor.outdoor_temperature"
seasonal_learning: true  # Auto-enabled when outdoor sensor present
```

**Technical Details:**
- Minimum 3 samples per temperature bucket for statistical reliability
- Median-based calculations for robust predictions
- Graceful fallback to general patterns when insufficient seasonal data
- Storage integration for persistent seasonal patterns

## Operating Modes

### Normal Mode
Default operation with standard learning and offset application.

### Away Mode
```yaml
away_mode_temperature: 26  # Fixed temperature (10-35°C)
```
- Sets fixed temperature regardless of normal target
- Reduces energy consumption during absence
- Automatically resumes normal operation when away mode disabled

### Sleep Mode  
```yaml
sleep_mode_offset: 2  # Additional offset (-5 to +5°C)
```
- Applies additional offset for quieter night operation
- Typically positive offset for slightly warmer sleep temperature
- Can be negative for cooler sleep preferences

### Boost Mode
```yaml
boost_mode_offset: -3  # Aggressive cooling (-10 to 0°C)
```
- Applies aggressive offset for rapid cooling
- Always negative for enhanced cooling effect
- Useful for quickly reaching target temperature

## Dashboard and Monitoring

### Automatic Sensor Creation
Five sensor entities are automatically created for each Smart Climate device:

1. **Current Offset** (`sensor.{entity}_offset_current`)
   - Real-time temperature offset in °C
   - Updates every coordinator cycle

2. **Learning Progress** (`sensor.{entity}_learning_progress`)  
   - Learning completion percentage (0-100%)
   - Based on sample count and confidence factors

3. **Current Accuracy** (`sensor.{entity}_accuracy_current`)
   - Current prediction accuracy percentage
   - Multi-factor calculation including condition diversity

4. **Calibration Status** (`sensor.{entity}_calibration_status`)
   - Shows current calibration phase
   - "Active Learning", "Calibrating", "Stable", etc.

5. **Hysteresis State** (`sensor.{entity}_hysteresis_state`)
   - AC behavior state monitoring
   - "idle", "cooling", "heating", "learning_hysteresis"

### Dashboard Generation Service
```yaml
service: smart_climate.generate_dashboard
data:
  climate_entity_id: climate.smart_climate_living_room
```
- Generates complete dashboard YAML configuration
- Automatically replaces entity IDs in template
- Delivered via persistent notification for easy copy/paste
- No manual YAML editing required

## Power Monitoring Integration

### Enhanced Learning Accuracy
When a power sensor is configured:
- **AC State Detection**: Accurately detects when AC is on/off/idle
- **Hysteresis Learning**: Learns AC start/stop temperature thresholds
- **Power Pattern Analysis**: Understands AC behavior patterns

### Power Thresholds
```yaml
power_idle_threshold: 50    # Below this = AC idle/off (10-500W)
power_min_threshold: 150    # Minimum operation power (50-1000W)  
power_max_threshold: 800    # Maximum operation power (100-5000W)
```

### Calibration Status
With power monitoring, calibration becomes more intelligent:
- Detects stable states when AC is idle AND temperatures converged
- Caches offsets only during stable periods
- Prevents feedback loops during active cooling/heating

## Safety Features

### Temperature Limits
```yaml
min_temperature: 16  # Minimum allowed temperature
max_temperature: 30  # Maximum allowed temperature
```

### Offset Limits  
```yaml
max_offset: 5.0  # Maximum offset in either direction (±5°C)
```

### Gradual Adjustments
```yaml
gradual_adjustment_rate: 0.5  # Temperature change per cycle (0.1-2.0°C)
```

### Learning Controls
- **Learning Switch**: Enable/disable learning without losing data
- **Reset Training Data**: Clear all learned patterns to start fresh
- **Manual Overrides**: Always available regardless of learning state

## Entity Attributes

### Climate Entity Attributes
All Smart Climate entities expose comprehensive diagnostic information:

#### Basic Information
- `current_offset`: Current temperature offset being applied
- `learning_enabled`: Whether learning is currently active
- `confidence_level`: Learning confidence (0.0-1.0)
- `sample_count`: Number of training samples collected

#### Learning Diagnostics  
- `avg_accuracy`: Average prediction accuracy
- `calibration_status`: Current calibration phase
- `hysteresis_state`: AC behavior state
- `last_learning_update`: Timestamp of last learning update

#### Advanced Diagnostics (v1.3.0)
- `adaptive_delay_learned`: Learned feedback delay in seconds
- `adaptive_delay_learning`: Whether delay learning is active
- `forecast_active_strategy`: Current weather strategy details
- `forecast_next_update`: Next forecast update time
- `seasonal_patterns_count`: Number of seasonal patterns learned
- `seasonal_current_bucket`: Current outdoor temperature bucket

### Switch Entity Attributes
The learning control switch provides additional diagnostics:
- `learning_started_at`: Timestamp when learning was enabled
- `save_count`: Number of successful data saves
- `failed_save_count`: Number of failed save attempts
- `last_save_time`: Timestamp of last successful save

## Configuration Options Summary

### Required Configuration
```yaml
climate_entity: climate.your_ac        # Climate entity to wrap
room_sensor: sensor.room_temperature   # Reference temperature sensor
```

### Optional Sensors
```yaml
outdoor_sensor: sensor.outdoor_temperature  # For seasonal adaptation
power_sensor: sensor.ac_power_consumption   # For enhanced learning
weather_entity: weather.home                # For forecast integration
```

### Learning Parameters
```yaml
ml_enabled: true                    # Enable machine learning (default: true)
learning_enabled: true             # Enable learning data collection (default: true)
adaptive_delay: false              # Enable adaptive delays (default: false)
seasonal_learning: true            # Enable seasonal adaptation (auto when outdoor sensor)
```

### Behavioral Settings
```yaml
update_interval: 180               # Update frequency in seconds (60-3600)
feedback_delay: 45                 # Base feedback delay in seconds (10-300)
gradual_adjustment_rate: 0.5       # Rate of temperature changes (0.1-2.0)
max_offset: 5.0                   # Maximum offset limit (1.0-10.0)
```

### Mode Configuration
```yaml
away_mode_temperature: 26          # Away mode fixed temp (10-35°C)
sleep_mode_offset: 2               # Sleep mode offset (-5 to +5°C)
boost_mode_offset: -3              # Boost mode offset (-10 to 0°C)
```

### Data Persistence
```yaml
save_interval: 60                  # Auto-save interval in minutes (5-1440)
```

## Feature Compatibility Matrix

| Feature | Requires | Optional | Benefits |
|---------|----------|----------|----------|
| **Basic Offset** | Room sensor | - | Temperature accuracy |
| **Learning** | Room sensor | Power sensor | Adaptive improvement |
| **Hysteresis Learning** | Power sensor | - | AC behavior understanding |
| **Adaptive Delays** | Room sensor | Power sensor | Timing optimization |
| **Weather Integration** | Weather entity | - | Predictive adjustments |
| **Seasonal Adaptation** | Outdoor sensor | - | Seasonal accuracy |
| **Dashboard** | - | - | Visual monitoring |

## Performance Characteristics

### System Requirements
- **Memory**: <10MB additional RAM usage
- **CPU**: <1ms typical response time
- **Storage**: <1MB for learned patterns and configuration
- **Network**: Minimal (only for weather forecasts if enabled)

### Update Frequencies
- **Core Updates**: Every 180 seconds (configurable 60-3600s)
- **Sensor Updates**: Every 30 seconds (dashboard sensors)
- **Weather Updates**: Every 30 minutes (with throttling)
- **Learning**: Continuous during operation
- **Persistence**: Every 60 minutes (configurable 5-1440 minutes)

### Data Retention
- **Learning Patterns**: 30-60 days (configurable)
- **Seasonal Data**: 45 days
- **Forecast Cache**: 24 hours
- **Diagnostic Logs**: Per Home Assistant settings

This features guide provides comprehensive coverage of all Smart Climate Control capabilities. For installation and setup instructions, see the [Installation Guide](installation.md). For troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).