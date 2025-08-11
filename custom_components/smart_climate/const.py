"""ABOUTME: Constants for the Smart Climate Control integration.
Defines domain name and configuration keys for the integration."""

# Domain name for the integration
DOMAIN = "smart_climate"

# Platforms supported by this integration
PLATFORMS = ["climate", "switch", "button", "sensor", "binary_sensor"]

# Configuration keys
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_ROOM_SENSOR = "room_sensor"
CONF_OUTDOOR_SENSOR = "outdoor_sensor"
CONF_POWER_SENSOR = "power_sensor"
CONF_MAX_OFFSET = "max_offset"
CONF_MIN_TEMPERATURE = "min_temperature"
CONF_MAX_TEMPERATURE = "max_temperature"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ML_ENABLED = "ml_enabled"
CONF_AWAY_TEMPERATURE = "away_temperature"
CONF_SLEEP_OFFSET = "sleep_offset"
CONF_BOOST_OFFSET = "boost_offset"
CONF_GRADUAL_ADJUSTMENT_RATE = "gradual_adjustment_rate"
CONF_FEEDBACK_DELAY = "feedback_delay"
CONF_ENABLE_LEARNING = "enable_learning"
CONF_POWER_IDLE_THRESHOLD = "power_idle_threshold"
CONF_POWER_MIN_THRESHOLD = "power_min_threshold"
CONF_POWER_MAX_THRESHOLD = "power_max_threshold"
CONF_DEFAULT_TARGET_TEMPERATURE = "default_target_temperature"
CONF_ENABLE_RETRY = "enable_retry"
CONF_MAX_RETRY_ATTEMPTS = "max_retry_attempts"
CONF_INITIAL_TIMEOUT = "initial_timeout"
CONF_SAVE_INTERVAL = "save_interval"
CONF_ADAPTIVE_DELAY = "adaptive_delay"
CONF_PREDICTIVE = "predictive"
CONF_DELAY_LEARNING_TIMEOUT = "delay_learning_timeout"

# Seasonal learning constants
SEASONAL_LEARNER_STORAGE_VERSION = 1
POST_COOL_RISE_PERIOD_MINUTES = 10  # How long to wait after cooling stops to measure stabilized temp
SEASONAL_SAVE_INTERVAL_MINUTES = 15  # How often to persist seasonal learner data

# Weather forecast configuration keys
CONF_FORECAST_ENABLED = "forecast_enabled"
CONF_WEATHER_ENTITY = "weather_entity"
CONF_FORECAST_STRATEGIES = "forecast_strategies"

# Forecast strategy configuration keys
CONF_STRATEGY_NAME = "strategy_name"
CONF_STRATEGY_ENABLED = "strategy_enabled"
CONF_STRATEGY_TYPE = "strategy_type"

# Heat wave strategy configuration keys
CONF_HEAT_WAVE_TEMP_THRESHOLD = "heat_wave_temp_threshold"
CONF_HEAT_WAVE_MIN_DURATION_HOURS = "heat_wave_min_duration_hours"
CONF_HEAT_WAVE_LOOKAHEAD_HOURS = "heat_wave_lookahead_hours"
CONF_HEAT_WAVE_PRE_ACTION_HOURS = "heat_wave_pre_action_hours"
CONF_HEAT_WAVE_ADJUSTMENT = "heat_wave_adjustment"

# Clear sky strategy configuration keys
CONF_CLEAR_SKY_CONDITION = "clear_sky_condition"
CONF_CLEAR_SKY_MIN_DURATION_HOURS = "clear_sky_min_duration_hours"
CONF_CLEAR_SKY_LOOKAHEAD_HOURS = "clear_sky_lookahead_hours"
CONF_CLEAR_SKY_PRE_ACTION_HOURS = "clear_sky_pre_action_hours"
CONF_CLEAR_SKY_ADJUSTMENT = "clear_sky_adjustment"

# Outlier detection configuration keys
CONF_OUTLIER_DETECTION_ENABLED = "outlier_detection_enabled"
CONF_OUTLIER_SENSITIVITY = "outlier_sensitivity"

# Thermal efficiency configuration keys (v1.4.0)
CONF_THERMAL_EFFICIENCY_ENABLED = "thermal_efficiency_enabled"
CONF_PREFERENCE_LEVEL = "preference_level"
CONF_SHADOW_MODE = "shadow_mode"
CONF_PRIMING_DURATION_HOURS = "priming_duration_hours"
CONF_RECOVERY_DURATION_MINUTES = "recovery_duration_minutes"
CONF_PROBE_DRIFT_LIMIT = "probe_drift_limit"
CONF_CALIBRATION_IDLE_MINUTES = "calibration_idle_minutes"
CONF_CALIBRATION_DRIFT_THRESHOLD = "calibration_drift_threshold"

# Default values
DEFAULT_MAX_OFFSET = 5.0
DEFAULT_MIN_TEMPERATURE = 16.0
DEFAULT_MAX_TEMPERATURE = 30.0
DEFAULT_UPDATE_INTERVAL = 180
DEFAULT_ML_ENABLED = True
DEFAULT_AWAY_TEMPERATURE = 19.0
DEFAULT_SLEEP_OFFSET = 1.0
DEFAULT_BOOST_OFFSET = -2.0
DEFAULT_GRADUAL_ADJUSTMENT_RATE = 0.5
DEFAULT_FEEDBACK_DELAY = 45
DEFAULT_ENABLE_LEARNING = False
DEFAULT_POWER_IDLE_THRESHOLD = 50
DEFAULT_POWER_MIN_THRESHOLD = 100
DEFAULT_POWER_MAX_THRESHOLD = 250
DEFAULT_TARGET_TEMPERATURE = 24.0
DEFAULT_ENABLE_RETRY = True
DEFAULT_MAX_RETRY_ATTEMPTS = 4
DEFAULT_INITIAL_TIMEOUT = 60
DEFAULT_SAVE_INTERVAL = 3600
DEFAULT_ADAPTIVE_DELAY = True
DEFAULT_DELAY_LEARNING_TIMEOUT = 20

# Delay learning timeout constraints
MIN_DELAY_LEARNING_TIMEOUT = 5
MAX_DELAY_LEARNING_TIMEOUT = 60

# Weather forecast default values
DEFAULT_FORECAST_ENABLED = False

# Heat wave strategy default values
DEFAULT_HEAT_WAVE_TEMP_THRESHOLD = 29.0
DEFAULT_HEAT_WAVE_MIN_DURATION_HOURS = 5
DEFAULT_HEAT_WAVE_LOOKAHEAD_HOURS = 24
DEFAULT_HEAT_WAVE_PRE_ACTION_HOURS = 2
DEFAULT_HEAT_WAVE_ADJUSTMENT = -2.0

# Clear sky strategy default values
DEFAULT_CLEAR_SKY_CONDITION = "sunny"
DEFAULT_CLEAR_SKY_MIN_DURATION_HOURS = 6
DEFAULT_CLEAR_SKY_LOOKAHEAD_HOURS = 12
DEFAULT_CLEAR_SKY_PRE_ACTION_HOURS = 1
DEFAULT_CLEAR_SKY_ADJUSTMENT = -1.0

# Outlier detection default values
DEFAULT_OUTLIER_DETECTION_ENABLED = True  # Enable outlier detection by default
DEFAULT_OUTLIER_SENSITIVITY = 2.5  # Modified Z-score threshold for outlier detection
DEFAULT_OUTLIER_HISTORY_SIZE = 100  # Number of historical samples to keep for analysis
DEFAULT_OUTLIER_MIN_SAMPLES = 10  # Minimum samples required before outlier detection starts
DEFAULT_OUTLIER_TEMP_BOUNDS = (0, 40)  # Temperature bounds (min, max) in Celsius for validation
DEFAULT_OUTLIER_POWER_BOUNDS = (0, 5000)  # Power bounds (min, max) in watts for validation

# Service names
SERVICE_SET_OFFSET = "set_offset"
SERVICE_RESET_OFFSET = "reset_offset"
SERVICE_PAUSE_ML = "pause_ml"
SERVICE_RESUME_ML = "resume_ml"

# Temperature thresholds
TEMP_DEVIATION_THRESHOLD = 0.5  # degrees Celsius

# ML input validation constants
CONF_VALIDATION_OFFSET_MIN = "validation_offset_min"
CONF_VALIDATION_OFFSET_MAX = "validation_offset_max"
CONF_VALIDATION_TEMP_MIN = "validation_temp_min"
CONF_VALIDATION_TEMP_MAX = "validation_temp_max"
CONF_VALIDATION_RATE_LIMIT_SECONDS = "validation_rate_limit_seconds"

# ML input validation default values
DEFAULT_VALIDATION_OFFSET_MIN = -10.0  # degrees C/F
DEFAULT_VALIDATION_OFFSET_MAX = 10.0   # degrees C/F
DEFAULT_VALIDATION_TEMP_MIN = 10.0     # degrees C/F (reasonable indoor range)
DEFAULT_VALIDATION_TEMP_MAX = 40.0     # degrees C/F (reasonable indoor range)
DEFAULT_VALIDATION_RATE_LIMIT_SECONDS = 60  # minimum seconds between samples

# HVAC modes that allow temperature adjustments
ACTIVE_HVAC_MODES = ["cool", "heat", "heat_cool", "dry", "auto"]

# HVAC modes that allow learning data collection (subset of ACTIVE_HVAC_MODES)
LEARNING_HVAC_MODES = ["cool", "heat", "heat_cool", "auto"]

# Thermal efficiency constants (v1.4.0)
MIN_OFF_TIME_SECONDS = 600   # 10 minutes minimum AC off time
MIN_ON_TIME_SECONDS = 300    # 5 minutes minimum AC on time

# Thermal efficiency default values
DEFAULT_THERMAL_EFFICIENCY_ENABLED = False  # Disabled by default for existing installations
DEFAULT_PREFERENCE_LEVEL = "balanced"
DEFAULT_PRIMING_DURATION_HOURS = 36
DEFAULT_RECOVERY_DURATION_MINUTES = 45
DEFAULT_PROBE_DRIFT_LIMIT = 2.0
DEFAULT_CALIBRATION_IDLE_MINUTES = 30
DEFAULT_CALIBRATION_DRIFT_THRESHOLD = 0.1

# Preference level options
PREFERENCE_LEVELS = [
    "max_comfort",
    "comfort_priority", 
    "balanced",
    "savings_priority",
    "max_savings"
]
PRIMING_DURATION_HOURS = 24  # 24 hours initial learning phase
RECOVERY_DURATION_MINUTES = 30  # 30 minutes recovery after mode changes

# Version constant for thermal efficiency features
THERMAL_EFFICIENCY_VERSION = "1.4.0"

# Final integration constants (Step 3.6)
DEFAULT_SHADOW_MODE = True  # Override - safe default for observation only 
INSIGHTS_UPDATE_INTERVAL = 3600  # 1 hour insights generation interval
MAX_PROBE_DURATION = 7200  # 2 hours maximum probe duration