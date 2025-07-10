# Smart Climate Confidence Calculation

## The Problem with the Current Confidence Calculation

The current confidence calculation in the Smart Climate integration has a significant limitation: it gets stuck at 0.5 (50%) and never improves, even as the system collects more data and learns patterns. This happens because the confidence is calculated based only on available sensor data, not on the learning system's actual performance and maturity.

### Current Implementation Issues

The existing `_calculate_confidence()` method:
- Starts with a base confidence of 0.5
- Adds 0.2 if outdoor temperature sensor is available
- Adds 0.2 if power sensor is available  
- Adds 0.1 for special modes (away, sleep, boost)
- **Result**: Maximum 1.0 if all sensors present, but typically stuck at 0.5-0.7

This approach doesn't consider:
- How many samples have been collected
- How diverse the conditions are
- How consistent the predictions are
- Whether the system has seen different operating scenarios

## The New Multi-Factor Confidence Calculation

The new approach calculates confidence based on multiple factors that actually reflect the system's learning maturity and reliability:

### 1. Sample Count (Learning Maturity)
- **0-10 samples**: Very low confidence (0.0-0.2)
- **10-50 samples**: Low to moderate confidence (0.2-0.5)
- **50-200 samples**: Moderate to good confidence (0.5-0.8)
- **200+ samples**: High confidence potential (0.8-1.0)

The confidence from sample count uses a logarithmic curve that reflects diminishing returns - the first samples provide the most learning value.

### 2. Condition Diversity
The system tracks how many different operating conditions it has experienced:

#### Temperature Ranges
- Different room temperature ranges (e.g., 18-20°C, 20-22°C, 22-24°C, etc.)
- Different AC internal temperature readings
- Various outdoor temperature conditions (if sensor available)

#### Power States
- Idle periods
- Low power usage
- Moderate power usage
- High power usage

#### Operating Modes
- Normal operation
- Away mode
- Sleep mode
- Boost mode

**Confidence boost**: Up to +0.2 based on diversity of conditions seen

### 3. Time Coverage
The system tracks which hours of the day have collected data:
- Morning patterns (6 AM - 12 PM)
- Afternoon patterns (12 PM - 6 PM)
- Evening patterns (6 PM - 12 AM)
- Night patterns (12 AM - 6 AM)

**Confidence boost**: Up to +0.15 for comprehensive time coverage

### 4. Prediction Consistency
When the learning system makes predictions, it tracks:
- How close predictions are to actual required offsets
- Standard deviation of prediction errors
- Trend of improving accuracy over time

**Confidence adjustment**: ±0.15 based on prediction reliability

## How Confidence Progresses

### Phase 1: Initial Learning (0-20% Confidence)
- **Samples**: 0-10
- **Characteristics**: 
  - System just starting to collect data
  - High uncertainty in predictions
  - Mostly using rule-based calculations
- **User Experience**: "Just starting to learn your AC's behavior"

### Phase 2: Early Learning (20-40% Confidence)
- **Samples**: 10-50
- **Characteristics**:
  - Basic patterns emerging
  - Some time-of-day patterns identified
  - Limited condition diversity
- **User Experience**: "Learning your daily patterns"

### Phase 3: Moderate Confidence (40-60% Confidence)
- **Samples**: 50-150
- **Characteristics**:
  - Solid time patterns established
  - Multiple operating conditions observed
  - Predictions becoming more reliable
- **User Experience**: "Understanding your AC's characteristics"

### Phase 4: Good Confidence (60-80% Confidence)
- **Samples**: 150-300
- **Characteristics**:
  - Comprehensive condition coverage
  - Strong prediction accuracy
  - Handles edge cases well
- **User Experience**: "Reliably optimizing your comfort"

### Phase 5: High Confidence (80-100% Confidence)
- **Samples**: 300+
- **Characteristics**:
  - Full seasonal patterns captured
  - Excellent prediction accuracy
  - Optimal performance across all conditions
- **User Experience**: "Fully optimized for your environment"

## What Confidence Levels Mean for Users

### 0-20%: Just Starting to Learn
- The system is collecting initial data
- Offsets are primarily rule-based
- Give it a few days to learn your patterns
- Manual adjustments may be needed

### 20-40%: Early Learning Phase  
- Basic patterns are being identified
- Time-of-day adjustments starting to work
- System needs more diverse conditions
- Performance will improve daily

### 40-60%: Moderate Confidence
- System understands your typical usage
- Good performance during common conditions
- May struggle with unusual situations
- Most users see good comfort at this level

### 60-80%: Good Confidence
- Reliable predictions across most scenarios
- Handles temperature changes smoothly
- Power-based optimizations working well
- Minimal manual intervention needed

### 80-100%: High Confidence
- System fully understands your AC's behavior
- Optimal comfort in all conditions
- Predictive adjustments prevent issues
- Maximum energy efficiency achieved

## Technical Implementation Details

### Confidence Calculation Formula

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

### Key Improvements

1. **Dynamic Growth**: Confidence grows naturally as the system learns
2. **Multi-dimensional**: Considers multiple aspects of learning maturity
3. **Predictive Feedback**: Uses actual prediction accuracy to adjust confidence
4. **Meaningful Progress**: Users see confidence increase as system improves
5. **Realistic Expectations**: Confidence reflects actual system capabilities

### Integration with Learning System

The new confidence calculation integrates with:
- `LightweightOffsetLearner`: Provides sample counts and time patterns
- `HysteresisLearner`: Indicates power pattern understanding
- `OffsetEngine`: Tracks prediction accuracy and conditions
- Dashboard sensors: Display real-time confidence to users

This approach ensures that confidence is a true reflection of the system's learning progress and prediction reliability, providing users with meaningful feedback about their Smart Climate system's optimization level.