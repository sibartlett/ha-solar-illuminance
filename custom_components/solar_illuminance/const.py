"""Constants for Solar Illuminance integration."""

from datetime import timedelta

DOMAIN = "solar_illuminance"
DEFAULT_NAME = "Solar Illuminance"
MIN_SCAN_INTERVAL_MIN = 0.5
DEFAULT_SCAN_INTERVAL_MIN = 5
DEFAULT_FALLBACK = 10
# How long a weather data source can be unavailable before there's a repair.
ISSUE_AFTER = timedelta(hours=1)
# Lux per Watts/M²
LUX_PER_WPSM = 120

CONF_FALLBACK = "fallback"
