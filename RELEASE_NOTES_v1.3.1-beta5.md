# Smart Climate Control v1.3.1-beta5

## 🐛 Weather Configuration Fix

This release fixes a critical issue where the weather forecast integration would show as "Disabled" on the dashboard despite being properly configured through the UI.

### What was broken
When users enabled weather forecasting through the UI configuration and selected their weather entity, the Smart Climate would fail to initialize the ForecastEngine because:
- The config flow saves a flat configuration structure (`forecast_enabled: true`, `weather_entity: weather.home`)
- The ForecastEngine expected a nested `predictive` configuration structure with strategies

### The fix
- Added a new `config_helpers.py` module that translates flat configuration to the nested structure at runtime
- Modified `climate.py` to use this translation when `CONF_FORECAST_ENABLED` is True
- Maintains full backward compatibility with legacy `CONF_PREDICTIVE` configurations
- No breaking changes - existing configurations continue to work

### Impact
Users who have weather forecasting enabled in their configuration will now see:
- "Weather Integration: Enabled" on the dashboard
- Predictive temperature offsets based on weather forecasts
- Active weather strategies (heat wave pre-cooling, clear sky optimization)

### Technical details
- Created comprehensive test suite (67 tests) following TDD methodology
- Added translation layer to convert flat config keys to nested predictive structure
- Fixed key mismatches between config_helpers and forecast_engine expectations
- Enhanced documentation with troubleshooting information

### Installation
Update through HACS with "Show beta versions" enabled, or manually download from the releases page.

### Testing
The fix has been thoroughly tested with:
- Fresh installations with weather config
- Existing installations enabling weather
- Legacy configuration format migrations
- Weather entity unavailability scenarios
- All strategy activation scenarios

### Acknowledgments
Thank you to the users who reported this issue and helped identify the root cause.

---
**Full Changelog**: https://github.com/VectorBarks/smart-climate/compare/v1.3.1-beta4...v1.3.1-beta5