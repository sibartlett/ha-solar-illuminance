"""Solar Illuminance Sensor."""

import asyncio
from collections.abc import Coroutine
from typing import Any

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_UNIQUE_ID,
    EVENT_CORE_CONFIG_UPDATE,
    SERVICE_RELOAD,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.helpers.sun import get_astral_observer
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol

from .const import DOMAIN
from .sensor import LOC_ELEV, SOLAR_ILLUMINANCE_SCHEMA

_SOLAR_ILLUMINANCE_SCHEMA = vol.Schema(
    SOLAR_ILLUMINANCE_SCHEMA
    | {
        vol.Required(CONF_UNIQUE_ID): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {vol.Optional(DOMAIN): vol.All(cv.ensure_list, [_SOLAR_ILLUMINANCE_SCHEMA])},
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = [Platform.SENSOR]


async def _async_process_config(
    hass: HomeAssistant, config: ConfigType | None, run_immediately: bool = True
) -> None:
    """Process illuminance config."""
    if not config or not (configs := config.get(DOMAIN)):
        configs = []
    unique_ids = [config[CONF_UNIQUE_ID] for config in configs]
    tasks: list[Coroutine[Any, Any, Any]] = []

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.source != SOURCE_IMPORT:
            continue
        if entry.unique_id not in unique_ids:
            tasks.append(hass.config_entries.async_remove(entry.entry_id))

    for conf in configs:
        tasks.append(  # noqa: PERF401
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=conf.copy()
            )
        )

    if not tasks:
        return

    if run_immediately:
        await asyncio.gather(*tasks)
    else:
        for task in tasks:
            hass.async_create_task(task)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up composite integration."""

    async def async_get_loc_elev(event: Event | None = None) -> None:
        """Get astral observer for current HA configuration."""
        if event is not None and not event.data:
            return
        hass.data[LOC_ELEV] = get_astral_observer(hass)

    async def reload_config(call: ServiceCall | None = None) -> None:
        """Reload configuration."""
        await _async_process_config(
            hass, await async_integration_yaml_config(hass, DOMAIN)
        )

    await async_get_loc_elev()
    await _async_process_config(hass, config, run_immediately=False)
    async_register_admin_service(hass, DOMAIN, SERVICE_RELOAD, reload_config)
    hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, async_get_loc_elev)

    return True


async def entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry update."""
    if not entry.state.recoverable:
        return
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up config entry."""
    entry.async_on_unload(entry.add_update_listener(entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
