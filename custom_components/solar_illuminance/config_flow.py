"""Config flow for Solar Illuminance integration."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
import probatio as vol

from .const import (
    CONF_FALLBACK,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MIN_SCAN_INTERVAL_MIN,
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=MIN_SCAN_INTERVAL_MIN, step=0.5, mode=NumberSelectorMode.BOX
            )
        ),
        vol.Optional(CONF_ENTITY_ID): EntitySelector(
            EntitySelectorConfig(domain=["sensor", "weather"])
        ),
        vol.Optional(CONF_FALLBACK): NumberSelector(
            NumberSelectorConfig(min=1, max=10, step="any", mode=NumberSelectorMode.BOX)
        ),
    }
)


def _suggested_options(options: Mapping[str, Any]) -> dict[str, Any]:
    """Return the values to show in the options form: the current ones, or defaults."""
    suggested = {
        CONF_SCAN_INTERVAL: options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MIN),
    }
    for key in (CONF_ENTITY_ID, CONF_FALLBACK):
        if (value := options.get(key)) is not None:
            suggested[key] = value
    return suggested


class SolarIlluminanceConfigFlow(ConfigFlow, domain=DOMAIN):
    """Solar Illuminance config flow."""

    VERSION = 1

    _name: str = DEFAULT_NAME

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SolarIlluminanceOptionsFlow:
        """Get the options flow for this handler."""
        return SolarIlluminanceOptionsFlow()

    async def async_step_user(
        self, _: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start user config flow."""
        return await self.async_step_name()

    async def async_step_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Get name."""
        if user_input is not None:
            self._name = user_input[CONF_NAME]
            return await self.async_step_options()

        schema = {vol.Required(CONF_NAME, default=self._name): TextSelector()}
        return self.async_show_form(
            step_id="name", data_schema=vol.Schema(schema), last_step=False
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Get sensor options."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name, data={}, options=user_input
            )

        return self.async_show_form(
            step_id="options",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, _suggested_options({})
            ),
        )


class SolarIlluminanceOptionsFlow(OptionsFlow):
    """Solar Illuminance integration options flow."""

    init_step = "options"

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change sensor options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="options",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, _suggested_options(self.config_entry.options)
            ),
        )
