"""Solar Illuminance Sensor."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.event import async_track_entity_registry_updated_event

from .const import DOMAIN

# Sensors are set up in the UI; YAML configuration is reported as an error.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.SENSOR]


async def entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry update."""
    if not entry.state.recoverable:
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    entry.async_on_unload(entry.add_update_listener(entry_updated))
    if weather_entity := entry.options.get(CONF_ENTITY_ID):
        entry.async_on_unload(
            async_track_entity_registry_updated_event(
                hass, weather_entity, _async_follow_rename(hass, entry)
            )
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _async_follow_rename(
    hass: HomeAssistant, entry: ConfigEntry
) -> Callable[[Event[er.EventEntityRegistryUpdatedData]], None]:
    """Return a listener that follows the weather data source's renames."""

    @callback
    def follow_rename(event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        """Use the weather data source's new entity ID; the entry then reloads.

        Only a rename changes the entity ID, and the entry is only updated, and
        reloaded, if its options change.
        """
        hass.config_entries.async_update_entry(
            entry, options={**entry.options, CONF_ENTITY_ID: event.data["entity_id"]}
        )

    return follow_rename


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
