"""Repair issues for problems users can fix themselves."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

# The translation keys of the weather data source issues. A sensor has at most
# one of them at a time.
WEATHER_SOURCE_MISSING = "weather_source_missing"
WEATHER_SOURCE_UNAVAILABLE = "weather_source_unavailable"
WEATHER_SOURCE_ISSUES = (WEATHER_SOURCE_MISSING, WEATHER_SOURCE_UNAVAILABLE)


@callback
def async_set_weather_source_issue(
    hass: HomeAssistant,
    entry_id: str,
    key: str | None,
    placeholders: dict[str, str] | None = None,
) -> None:
    """Raise a config entry's weather data source issue, or delete it if key is None."""
    for issue in WEATHER_SOURCE_ISSUES:
        issue_id = f"{issue}_{entry_id}"
        if issue != key:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
            continue
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=key,
            translation_placeholders=placeholders,
        )
