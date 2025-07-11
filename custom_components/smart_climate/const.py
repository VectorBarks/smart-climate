"""ABOUTME: Constants for the Smart Climate Control integration.
Defines domain name and configuration keys for the integration."""

# Domain name for the integration
DOMAIN = "smart_climate"

# Platforms supported by this integration
PLATFORMS = ["climate", "switch", "button", "sensor"]

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

# Service names
SERVICE_SET_OFFSET = "set_offset"
SERVICE_RESET_OFFSET = "reset_offset"
SERVICE_PAUSE_ML = "pause_ml"
SERVICE_RESUME_ML = "resume_ml"

# Temperature thresholds
TEMP_DEVIATION_THRESHOLD = 0.5  # degrees Celsius