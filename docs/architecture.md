# Architecture Documentation

This document describes the technical architecture of Smart Climate Control, explaining how components interact and the design decisions behind the implementation.

## Overview

Smart Climate Control follows a modular, loosely-coupled architecture that emphasizes reliability, testability, and maintainability. The integration creates a virtual climate entity that wraps existing climate devices, adding intelligence through offset calculations and learning capabilities.

## Core Design Principles

### Separation of Concerns
Each component has a single, well-defined responsibility:
- **Climate Entity**: User interface and Home Assistant integration
- **Offset Engine**: Temperature offset calculations and learning
- **Sensor Manager**: Sensor reading and availability monitoring
- **Mode Manager**: Operating mode logic and adjustments
- **Temperature Controller**: Command execution and safety limits
- **Data Store**: Persistence and data management

### Dependency Injection
All components use constructor-based dependency injection:
- Improves testability through easy mocking
- Reduces coupling between components
- Makes dependencies explicit and manageable
- Enables flexible configuration

### Fail-Safe Design
The system continues operating even when components fail:
- Missing sensors trigger graceful degradation
- Learning failures don't affect basic operation
- Persistence errors don't crash the system
- Network issues are handled transparently

## Component Architecture

### Component Interaction Diagram

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
The main climate entity that users interact with.

**Responsibilities**:
- Implements Home Assistant ClimateEntity interface
- Forwards commands to wrapped climate entity
- Applies calculated offsets to temperature commands
- Exposes current room temperature from sensors
- Manages preset modes and manual overrides

**Key Design Decisions**:
- Inherits directly from ClimateEntity for full compatibility
- Transparently wraps existing entities without modification
- Preserves all original entity capabilities
- Adds intelligence without breaking existing functionality

#### OffsetEngine
Calculates temperature offsets using rules and learning.

**Responsibilities**:
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
Provides intelligent pattern learning without heavy ML overhead.

**Responsibilities**:
- Time-of-day pattern recognition
- Environmental correlation learning
- Exponential smoothing for stability
- Confidence scoring for predictions
- JSON serialization for persistence

**Design Features**:
- <1ms prediction time requirement
- <1MB memory usage limit
- Incremental learning approach
- No external dependencies
- Graceful degradation without historical data

#### SensorManager
Manages all sensor interactions and monitoring.

**Responsibilities**:
- Read temperature values from sensors
- Monitor sensor availability
- Notify listeners of changes
- Handle sensor failures gracefully
- Provide fallback values when appropriate

**Sensor Types Managed**:
- Room temperature (required)
- Outdoor temperature (optional)
- Power consumption (optional)
- Internal AC temperature (via wrapped entity)

#### ModeManager
Handles operating modes and their effects.

**Responsibilities**:
- Track current operating mode
- Provide mode-specific adjustments
- Notify listeners of mode changes
- Validate mode transitions
- Apply mode-specific behaviors

**Supported Modes**:
- Normal: Standard operation
- Away: Fixed temperature
- Sleep: Quiet operation with offset
- Boost: Rapid cooling mode

#### TemperatureController
Manages temperature commands and safety.

**Responsibilities**:
- Apply offsets to temperature commands
- Enforce min/max temperature limits
- Implement gradual adjustments
- Send commands to wrapped entity
- Log all temperature changes

**Safety Features**:
- Hard limits on temperature range
- Maximum offset constraints
- Gradual adjustment rate limiting
- Command validation before execution

#### SmartClimateDataStore
Handles data persistence for learning patterns.

**Responsibilities**:
- Atomic file operations
- JSON serialization/deserialization
- Backup management
- Corruption recovery
- Migration between versions

**Design Decisions**:
- JSON format for human readability
- Atomic writes prevent corruption
- Automatic backups before writes
- Graceful handling of missing files

## Data Flow

### Temperature Setting Flow

1. User sets desired temperature (22°C)
2. SmartClimateEntity receives command
3. Coordinator provides current sensor data
4. OffsetEngine calculates required offset
5. TemperatureController applies offset and limits
6. Command sent to wrapped entity (20°C)
7. Feedback collected after delay
8. Learning system updates patterns

### Sensor Update Flow

1. Physical sensor reports new value
2. Home Assistant updates sensor entity
3. SensorManager detects state change
4. Notifies registered callbacks
5. Coordinator triggers update cycle
6. New offset calculated if needed
7. Temperature adjusted if required

### Learning Feedback Flow

1. Temperature adjustment made
2. Timer started for feedback delay
3. After delay, current offset measured
4. Comparison with prediction made
5. Error calculated and recorded
6. Learning patterns updated
7. Confidence scores adjusted
8. Data persisted to storage

## Integration Architecture

### Home Assistant Integration

The integration follows Home Assistant's architecture requirements:

**Setup Flow**:
```python
async def async_setup_entry(hass, entry, async_add_entities):
    # Create components with dependencies
    # Wire everything together
    # Start background tasks
    # Add entities to Home Assistant
```

**Config Flow**:
- Implements configuration UI
- Validates user input
- Creates config entries
- Supports options flow for updates

**Platform Structure**:
- `climate.py`: Climate platform implementation
- `switch.py`: Learning control switch
- `__init__.py`: Integration setup and coordination

### Entity Relationships

```
SmartClimateEntity
├── Wrapped Climate Entity (climate.original_ac)
├── Room Sensor (sensor.room_temperature)
├── Outdoor Sensor (sensor.outdoor_temp) [optional]
├── Power Sensor (sensor.ac_power) [optional]
└── Learning Switch (switch.smart_ac_learning)
```

### State Management

**Entity State**:
- Mirrors wrapped entity HVAC state
- Overrides current_temperature with room sensor
- Maintains user's target temperature separately
- Tracks applied offset in attributes

**Learning State**:
- Persisted to JSON files
- Loaded on startup
- Saved periodically and on shutdown
- Includes patterns, statistics, and metadata

## Design Patterns

### Observer Pattern
Used for component communication:
- SensorManager notifies of sensor changes
- ModeManager notifies of mode switches
- Reduces coupling between components
- Enables dynamic listener registration

### Strategy Pattern
Different calculation strategies:
- Rule-based offset calculation
- Learning-enhanced calculation
- Mode-specific adjustments
- Allows runtime strategy selection

### Factory Pattern
Component creation and wiring:
- Centralized in `__init__.py`
- Manages dependency injection
- Ensures proper initialization order
- Simplifies testing with mock factories

### Repository Pattern
Data persistence abstraction:
- DataStore provides storage interface
- Isolates persistence logic
- Enables easy testing
- Supports future storage backends

## Performance Considerations

### Optimization Strategies

**Caching**:
- Sensor values cached between updates
- Learning predictions cached by hour
- Offset calculations cached until inputs change

**Throttling**:
- Update cycles limited by interval
- Sensor updates debounced
- Learning updates batched
- File writes minimized

**Resource Limits**:
- Learning memory capped at 1MB
- Prediction time limited to 1ms
- File operations use async I/O
- Background tasks properly scheduled

### Scalability

The architecture scales well:
- Each climate entity independent
- Shared outdoor sensors supported
- Learning data per-entity
- No inter-entity communication required

## Security Considerations

### Input Validation
- All sensor inputs validated for type/range
- Entity IDs verified before use
- Configuration parameters checked
- Service calls sanitized

### Data Protection
- No sensitive data in logs
- Local storage only (no cloud)
- File permissions respected
- No network communication

### Error Handling
- All exceptions caught and logged
- Graceful degradation on errors
- No user data in error messages
- Safe defaults for all failures

## Testing Architecture

### Unit Testing
Each component tested in isolation:
- Mock dependencies injected
- Edge cases covered
- Error conditions tested
- Performance validated

### Integration Testing
Component interactions tested:
- Full setup flow
- Sensor state changes
- Mode transitions
- Learning feedback cycles

### Test Structure
```
tests/
├── Unit tests (per component)
├── Integration tests
├── Fixtures and mocks
└── Test utilities
```

## Extension Points

### Adding New Sensors
1. Extend SensorManager with new sensor type
2. Update OffsetInput data structure
3. Modify offset calculation logic
4. Add configuration support
5. Update tests

### Adding New Modes
1. Add mode to ModeManager
2. Define mode adjustments
3. Update configuration schema
4. Add mode-specific tests
5. Update documentation

### Alternative Learning Algorithms
1. Implement new learner class
2. Match existing interface
3. Update OffsetEngine integration
4. Add performance tests
5. Make configurable

## Future Architecture Considerations

### Planned Enhancements

**Multi-Zone Coordination**:
- Central coordinator for multiple zones
- Inter-zone communication protocol
- Shared learning insights
- Energy optimization across zones

**Advanced Learning**:
- Pluggable learning algorithms
- Neural network option
- Federated learning support
- Transfer learning between similar setups

**External Integrations**:
- Weather service integration
- Energy price awareness
- Occupancy detection
- Smart grid interaction

### Modular Extensions
The architecture supports future additions:
- New sensor types
- Additional operating modes
- Alternative storage backends
- Enhanced visualization
- External API endpoints

## Conclusion

Smart Climate Control's architecture prioritizes:
1. **Reliability**: Continues operating despite failures
2. **Maintainability**: Clear separation of concerns
3. **Testability**: Dependency injection throughout
4. **Extensibility**: Easy to add new features
5. **Performance**: Optimized for Home Assistant

This architecture ensures the integration remains stable, efficient, and easy to enhance while providing intelligent climate control for users.