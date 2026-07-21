"""Constants for LG OLED Control integration."""

DOMAIN = "lg_oled_control"

CONF_CLIENT_KEY = "client_key"

PLATFORMS = ["light", "button", "binary_sensor"]

# Connection settings
UPDATE_INTERVAL = 15  # seconds; fallback poll + reconnect loop
CONNECT_TIMEOUT = 8  # total bound on connect(); must fit inside UPDATE_INTERVAL
COMMAND_TIMEOUT = 10
PING_INTERVAL = 10  # keep-alive; library default of 1s is needlessly chatty
DISCONNECT_TIMEOUT = 5  # bound on disposing a client; a wedged one is abandoned

# Library-internal websocket connect retries (added in bscpylgtv 0.5.1 for
# webOS 25 TVs that intermittently drop the first connect). 3 attempts at
# timeout_connect=2s + 200ms spacing ≈ 6.6s worst case, inside CONNECT_TIMEOUT.
CONNECT_RETRY_ATTEMPTS = 3

# State subscriptions established at connect. current_app is required:
# client.is_on falls back to it when the power state reads "Unknown".
CLIENT_STATES = ["power", "current_app", "picture_settings"]

DEFAULT_BACKLIGHT = 50
DEFAULT_CONTRAST = 50
