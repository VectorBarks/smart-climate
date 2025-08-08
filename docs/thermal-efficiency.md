# Thermal Efficiency Management

This document explains Smart Climate Control's thermal efficiency features, including shadow mode, thermal monitoring, and the 6-state thermal management system.

## Overview

The Thermal Efficiency system optimizes AC operation by learning your room's thermal characteristics and making intelligent control decisions. It consists of five key components that can be individually enabled/disabled.

## Components

### 1. Thermal Model
- **Purpose**: Learns room's thermal physics (how fast it heats/cools)
- **Key Metrics**: Tau values (time constants) for heating and cooling
- **Always Enabled**: Required for other components to function

### 2. Thermal Preferences
- **Purpose**: Adapts comfort bands based on user preferences
- **Levels**: MAX_COMFORT, COMFORT_PRIORITY, BALANCED, SAVINGS_PRIORITY, MAX_SAVINGS
- **Default**: BALANCED

### 3. Thermal Monitor
- **Purpose**: Tracks thermal behavior anomalies and efficiency metrics
- **Status**: `monitor=False` (disabled by default)
- **Features When Enabled**:
  - Detects unusual heating/cooling rates
  - Identifies external disturbances (open windows, doors)
  - Tracks AC performance degradation
  - Monitors energy efficiency metrics

### 4. Thermal Controller
- **Purpose**: Actively controls AC based on thermal predictions
- **Status**: `controller=False` (disabled = shadow mode)
- **Shadow Mode**: When disabled, observes but doesn't control

### 5. Thermal Manager
- **Purpose**: Coordinates all thermal components
- **Always Enabled**: Required for thermal efficiency features

## Shadow Mode Operation

Shadow mode is activated when `controller=False`. This is the default during initial learning phases.

### What Shadow Mode Does
- **Observes**: Watches your AC's actual behavior
- **Learns**: Builds thermal model without disruption
- **Calculates**: Determines what it WOULD do if in control
- **Reports**: Shows decisions via sensors (e.g., "should_run=False")
- **Does NOT Control**: AC operates normally without Smart Climate intervention

### Why Shadow Mode Exists
1. **Safe Learning**: Avoids disrupting comfort during initial setup
2. **Validation**: Allows you to verify decisions before enabling control
3. **Gradual Transition**: Builds confidence before taking over

### Understanding Shadow Mode Logs

When you see:
```
thermal_decision=should_run=False ... shadow_mode=True
```

This means:
- Thermal manager thinks AC should be OFF
- But it's not controlling (shadow mode)
- AC continues running based on normal thermostat logic

## Thermal States

The system operates in six distinct states:

### 1. PRIMING (Initial 24-48 hours)
- **Purpose**: Conservative learning phase
- **Characteristics**:
  - Minimal offsets (±0.1-0.2°C)
  - Tight temperature windows
  - Conservative tau values (1.5/2.5 minutes)
  - Shadow mode enabled

### 2. DRIFTING
- **Purpose**: AC off, temperature naturally drifting
- **Behavior**: Monitors natural temperature change
- **Learning**: Refines tau_warming value

### 3. CORRECTING
- **Purpose**: AC actively cooling/heating
- **Behavior**: Monitors active temperature correction
- **Learning**: Refines tau_cooling value

### 4. RECOVERY
- **Purpose**: Recovering from mode changes
- **Trigger**: After switching between heat/cool modes
- **Duration**: Typically 15-30 minutes

### 5. PROBING
- **Purpose**: Active thermal characteristic learning
- **Method**: Controlled on/off cycles to measure response
- **Frequency**: Daily during calibration window

### 6. CALIBRATING
- **Purpose**: Fine-tuning offset predictions
- **Trigger**: After sufficient data collection
- **Result**: Optimized control parameters

## Configuration

### Via Home Assistant UI

Currently, thermal efficiency settings must be configured during integration setup or through YAML configuration. UI options for runtime configuration are planned for a future release.

### Via YAML Configuration

```yaml
smart_climate:
  - name: "Living Room Smart AC"
    climate_entity: climate.living_room_ac
    room_sensor: sensor.living_room_temperature
    
    # Enable thermal efficiency with all components
    thermal_efficiency:
      enabled: true
      components:
        model: true        # Always enabled when thermal_efficiency is true
        preferences: true  # Use comfort preference levels
        monitor: true     # Enable anomaly detection
        controller: true  # Exit shadow mode, enable active control
        manager: true     # Always enabled when thermal_efficiency is true
      
      # Comfort preference level
      comfort_preference: "BALANCED"  # or MAX_COMFORT, COMFORT_PRIORITY, SAVINGS_PRIORITY, MAX_SAVINGS
      
      # Thermal probing configuration
      probing:
        enabled: true
        window_start: "02:00"  # Start probing window (24h format)
        window_end: "06:00"    # End probing window
        frequency: "daily"     # How often to probe
```

## Enabling Active Control

To exit shadow mode and enable active AC control:

### Method 1: During Initial Setup
Configure thermal efficiency with `controller: true` in your YAML configuration.

### Method 2: After Initial Setup (Planned Feature)
UI configuration options will be added in a future release to toggle between shadow mode and active control.

### Prerequisites for Active Control
1. Complete PRIMING state (24-48 hours)
2. Sufficient learning data (36+ cycles recommended)
3. Stable thermal model (tau values learned)
4. Good prediction accuracy (>80% recommended)

## Monitoring Thermal Efficiency

### Key Sensors to Watch

**Thermal State**
- Entity: `sensor.{climate_name}_thermal_state`
- Shows current operational state (PRIMING, DRIFTING, etc.)

**Shadow Mode Status**
- Entity: `sensor.{climate_name}_shadow_mode`
- Values: "Enabled" (observing only) or "Disabled" (active control)

**Tau Values**
- Entities: `sensor.{climate_name}_tau_cooling` and `tau_warming`
- Time constants showing how fast your room responds
- PRIMING defaults: 1.5/2.5 minutes
- Learned values: typically 90/150 minutes

**Temperature Stability**
- Entity: `sensor.{climate_name}_temperature_stability_detected`
- Indicates if temperature is stable enough for decisions

## Understanding Thermal Decisions

### Decision Factors

The thermal manager considers:
1. **Current Temperature**: Is it within comfort bounds?
2. **Temperature Trend**: Is it moving toward or away from target?
3. **Thermal Momentum**: Will it overshoot if AC continues?
4. **Efficiency**: Can we coast to target without AC?
5. **Comfort Preference**: How tight should control be?

### Decision Output

When thermal manager says "should_run=False", it means:
- Room temperature is acceptable (within comfort window)
- No correction needed currently
- Continuing to run would waste energy
- Temperature will remain comfortable without AC

### Example Scenario

Your logs show:
```
Room: 23.7°C
Window: 22.2-25.2°C  
Decision: should_run=False
AC Status: Running (403W)
```

This indicates:
- Room is at 23.7°C (comfortable middle of range)
- No cooling needed per thermal model
- AC continues running because shadow_mode=True
- System is learning from this "unnecessary" cooling

## Thermal Monitor Features

When enabled (`monitor: true`), the system tracks:

### Efficiency Metrics
- Energy per degree of cooling/heating
- Overshoot frequency and magnitude
- Time to reach setpoint
- Cycling efficiency (longer cycles = better)

### Anomaly Detection
- **Open Window/Door**: Sudden increase in tau values
- **External Heat Source**: Unexpected temperature rises
- **AC Performance Issues**: Slower cooling than expected
- **Filter Problems**: Gradual performance degradation

### Alerts (Planned Feature)
Future versions will generate notifications for:
- Detected open windows/doors
- AC performance degradation
- Unusual energy consumption
- Maintenance recommendations

## Best Practices

### Initial Setup
1. Start with shadow mode (default)
2. Let system complete PRIMING (24-48 hours)
3. Monitor thermal decisions via sensors
4. Verify decisions align with your comfort
5. Enable controller when confident

### Comfort vs Efficiency
- **MAX_COMFORT**: Tightest control, highest energy use
- **BALANCED**: Good compromise (recommended)
- **MAX_SAVINGS**: Widest temperature swings, maximum efficiency

### Optimal Conditions for Learning
- Consistent AC usage patterns
- Minimal manual interventions
- Stable room conditions (doors/windows closed)
- Regular temperature changes (normal daily cycles)

## Troubleshooting

### Shadow Mode Won't Disable
- Ensure PRIMING phase is complete (check thermal_state sensor)
- Verify sufficient learning data exists
- Check configuration for `controller: true`

### Poor Thermal Predictions
- Verify tau values are realistic (not default 1.5/2.5)
- Check for external disturbances (open windows)
- Ensure consistent AC operation during learning
- Consider enabling thermal monitor for diagnostics

### AC Runs When Not Needed
- Normal in shadow mode (observing, not controlling)
- Check if controller is enabled for active control
- Verify comfort preferences aren't too strict

## Advanced Topics

### Tau Value Interpretation

**Tau Cooling** (τc)
- Time for room to cool 63% toward AC setpoint
- Typical values: 60-120 minutes
- Lower = room cools faster
- Affected by: AC power, room size, insulation

**Tau Warming** (τw)
- Time for room to warm 63% toward ambient
- Typical values: 90-180 minutes  
- Higher = room holds temperature longer
- Affected by: Insulation, external heat sources

### Thermal Probing

Active learning technique that:
1. Turns AC on/off in controlled patterns
2. Measures temperature response
3. Calculates accurate tau values
4. Typically runs during sleep hours (2-6 AM)
5. Minimal comfort disruption

### Integration with Other Features

**With Hysteresis Learning**
- Thermal efficiency uses cycle data
- Improves tau value estimates
- Better prediction of AC behavior

**With Seasonal Learning**
- Adjusts thermal model for outdoor conditions
- Accounts for seasonal heat load changes
- Improves efficiency in extreme weather

**With ML Offset Engine**
- Thermal predictions inform offset calculations
- Prevents overcooling/overheating
- Optimizes for both comfort and efficiency

## Future Enhancements

Planned improvements include:
- UI toggle for shadow mode/active control
- Real-time thermal monitor dashboard
- Push notifications for anomalies
- Automatic filter change reminders
- Integration with energy management systems
- Multi-zone thermal coordination

## Summary

The Thermal Efficiency system provides intelligent AC control through:
1. Learning your room's thermal characteristics
2. Operating safely in shadow mode during learning
3. Making efficiency-optimized decisions
4. Monitoring for anomalies and performance issues
5. Adapting to your comfort preferences

Start with shadow mode to build confidence, then enable active control for maximum efficiency and comfort.