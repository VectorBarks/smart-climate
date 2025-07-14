# Smart Climate Control v1.3.1-beta6

## 🚨 Critical Bug Fix: HVAC Mode Filtering

This release fixes a critical issue where Smart Climate was making inappropriate temperature adjustments and collecting invalid learning data when the AC was in non-active modes like `fan_only` or `off`.

### What was broken
The system was:
- Making temperature adjustments even when AC was in `fan_only` mode (meaningless since fan-only doesn't respond to temperature setpoints)
- Recording "learning" samples from `fan_only` mode, corrupting the ML model with temperature drift data
- Wasting energy with unnecessary AC commands in non-active modes

### The fix
**Two-part solution implemented with TDD methodology:**

**Part A: Temperature Adjustment Filtering**
- Added HVAC mode checking in `_apply_temperature_with_offset()`
- Temperature adjustments now only occur in active modes: `cool`, `heat`, `heat_cool`, `dry`, `auto`
- Skips adjustments entirely in `fan_only` and `off` modes
- Proper debug logging when adjustments are skipped

**Part B: Learning Data Protection**  
- Added HVAC mode filtering in `record_actual_performance()`
- Learning data only collected in modes where AC actively heats/cools: `cool`, `heat`, `heat_cool`, `auto`
- Prevents ML model poisoning from invalid samples in `fan_only`, `off`, and `dry` modes
- Extended OffsetInput model to include `hvac_mode` for complete traceability

### Impact
**Before the fix:**
- AC in fan_only mode: System makes temperature adjustments → No response → Records "bad" learning data
- Result: Corrupted ML model, wasted energy, meaningless commands

**After the fix:**
- AC in fan_only mode: System skips adjustments → No commands sent → No learning data recorded
- Result: Clean ML model, energy efficient, sensible behavior

### Technical implementation
- **New constants**: `ACTIVE_HVAC_MODES` and `LEARNING_HVAC_MODES` for proper filtering
- **Enhanced OffsetInput**: Now includes `hvac_mode` field for complete context tracking
- **Smart mode detection**: Coordinator passes HVAC state through entire processing chain
- **Backward compatibility**: No breaking changes, existing functionality preserved

### Test coverage
**21 comprehensive new tests** covering:
- 10 temperature adjustment tests verify proper mode filtering
- 11 learning data tests verify ML model protection  
- 100% test pass rate for all HVAC mode filtering functionality

### User experience
- **Fan only mode**: Silent operation, no unnecessary adjustments or learning
- **Off mode**: No smart climate operations attempted
- **Active modes** (`cool`, `heat`, `auto`, etc.): Unchanged behavior, all features work normally
- **Learning quality**: Improved ML accuracy by eliminating invalid training data
- **Energy efficiency**: Eliminates waste from meaningless commands

### Installation
Update through HACS with "Show beta versions" enabled, or manually download from the releases page.

### Issue reference
Resolves GitHub issue #56: "No temperature Adjustments when Smart Climate entity is not in cooling, dehumidifying or auto state"

---
**Full Changelog**: https://github.com/VectorBarks/smart-climate/compare/v1.3.1-beta5...v1.3.1-beta6