"""Constants for LG OLED Control integration."""

DOMAIN = "lg_oled_control"

CONF_CLIENT_KEY = "client_key"

PLATFORMS = ["light", "button", "binary_sensor"]

# Connection settings
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 1
