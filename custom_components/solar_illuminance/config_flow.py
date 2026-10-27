"""Config flow for Solar Illuminance integration."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_ENTITY_ID, CONF_MODE, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)

# Recent Home Assistant releases type flows for probatio, and still take
# voluptuous, its API-compatible predecessor, which 2026.7 needs.
if TYPE_CHECKING:
    import probatio as vol
else:
    import voluptuous as vol

from .const import (
    CONF_FALLBACK,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL_MIN,
    DOMAIN,
    MIN_SCAN_INTERVAL_MIN,
)
from .sensor import MODES

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODE): SelectSelector(
            SelectSelectorConfig(options=MODES, translation_key="mode")
        ),
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
        CONF_MODE: options.get(CONF_MODE, MODES[0]),
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
