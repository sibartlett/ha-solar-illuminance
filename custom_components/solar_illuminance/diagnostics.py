"""Diagnostics for the Solar Illuminance integration."""

from typing import Any

from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant

from .sensor import SolarIlluminanceConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SolarIlluminanceConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    weather_source = None
    if (entity_id := entry.options.get(CONF_ENTITY_ID)) and (
        state := hass.states.get(entity_id)
    ):
        weather_source = {
            "state": state.state,
            "attributes": dict(state.attributes),
            "last_changed": state.last_changed.isoformat(),
            "last_updated": state.last_updated.isoformat(),
        }
    return {
        "options": dict(entry.options),
        "sensor": entry.runtime_data.diagnostics(),
        "weather_source": weather_source,
    }
