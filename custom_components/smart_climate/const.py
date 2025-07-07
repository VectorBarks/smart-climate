"""ABOUTME: Constants for the Smart Climate Control integration.
Defines domain name and configuration keys for the integration."""

# Domain name for the integration
DOMAIN = "smart_climate"

# Platforms supported by this integration
PLATFORMS = ["climate", "switch"]

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

# Service names
SERVICE_SET_OFFSET = "set_offset"
SERVICE_RESET_OFFSET = "reset_offset"
SERVICE_PAUSE_ML = "pause_ml"
SERVICE_RESUME_ML = "resume_ml"