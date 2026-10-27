"""Works out a sensor's illuminance, for its illuminance and irradiance sensors."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from math import asin, cos, exp, radians, sin
from typing import Any

import astral.sun
from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
)
from homeassistant.components.weather.const import ATTR_WEATHER_CLOUD_COVERAGE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_SCAN_INTERVAL,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.sun import get_astral_observer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.util.dt as dt_util

from .const import CONF_FALLBACK, DEFAULT_FALLBACK, ISSUE_AFTER
from .issues import (
    WEATHER_SOURCE_MISSING,
    WEATHER_SOURCE_UNAVAILABLE,
    async_set_weather_source_issue,
)

_LOGGER = logging.getLogger(__name__)

Num = float | int

# Illuminance divisor for each weather condition. As well as the standard
# conditions, it has those of weather sources that report others: ecobee's
# snowy-heavy, tornado and hazy, and older AccuWeather integrations'
# mostlycloudy. None of these clash with a standard condition.

_DIVISOR_GROUPS: tuple[tuple[Num, tuple[str, ...]], ...] = (
    (
        10,
        (
            ATTR_CONDITION_LIGHTNING,
            ATTR_CONDITION_LIGHTNING_RAINY,
            ATTR_CONDITION_POURING,
            "snowy-heavy",
        ),
    ),
    (
        5,
        (
            ATTR_CONDITION_CLOUDY,
            ATTR_CONDITION_FOG,
            ATTR_CONDITION_RAINY,
            ATTR_CONDITION_SNOWY,
            ATTR_CONDITION_SNOWY_RAINY,
            ATTR_CONDITION_HAIL,
            ATTR_CONDITION_EXCEPTIONAL,
            "tornado",
        ),
    ),
    (3, ("mostlycloudy",)),
    (2, (ATTR_CONDITION_PARTLYCLOUDY, ATTR_CONDITION_WINDY_VARIANT, "hazy")),
    (1, (ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT, ATTR_CONDITION_WINDY)),
)
DIVISORS: dict[str, Num] = {
    condition: divisor
    for divisor, conditions in _DIVISOR_GROUPS
    for condition in conditions
}


type SolarIlluminanceConfigEntry = ConfigEntry[SolarIlluminanceCoordinator]


@dataclass(frozen=True)
class Illuminance:
    """An estimate of the outdoor illuminance, and how it was worked out."""

    # In lx, after the weather.
    value: float
    weather: str
    divisor: Num


def _illuminance(elev: Num) -> float:
    """Calculate illuminance from sun at given elevation."""
    elev_rad = radians(elev)
    u = sin(elev_rad)
    x = 753.66156
    s = asin(x * cos(elev_rad) / (x + 1))
    m = x * (cos(s) - u) + cos(s)
    m = exp(-0.2 * m) * u + 0.0289 * exp(-0.042 * m) * (
        1 + (elev + 90) * u / 57.29577951
    )
    return 133775 * m


def _cloud_coverage(value: Any) -> float | None:
    """Return a cloud coverage percentage, limited to 0-100, or None if invalid."""
    try:
        return min(max(0, float(value)), 100)
    except TypeError, ValueError:
        return None


class SolarIlluminanceCoordinator(DataUpdateCoordinator[Illuminance]):
    """Works out the illuminance at the update period and when the weather changes."""

    config_entry: SolarIlluminanceConfigEntry
    # The problem with the weather data last logged, if it hasn't been fixed.
    _problem: str | None = None
    # When the weather data source stopped having weather data, if it has none.
    _weather_unavailable_since: datetime | None = None

    def __init__(self, hass: HomeAssistant, entry: SolarIlluminanceConfigEntry) -> None:
        """Initialize from the config entry's options."""
        options = entry.options
        self._entry = entry
        self._weather_entity: str | None = options.get(CONF_ENTITY_ID)
        self._fallback: float = options.get(
            CONF_FALLBACK, DEFAULT_FALLBACK if self._weather_entity else 1
        )
        self._weather = "without weather data"
        self._divisor: Num = self._fallback
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=timedelta(minutes=options[CONF_SCAN_INTERVAL]),
        )

    async def async_start(self) -> None:
        """Work out the first value, and follow the weather."""
        self._get_divisor_from_weather_data(
            self.hass.states.get(self._weather_entity) if self._weather_entity else None
        )
        await self.async_config_entry_first_refresh()

        # A repair isn't raised while Home Assistant starts, so check as soon
        # as it has, rather than at the next update.
        if not self.hass.is_running:

            @callback
            def started(hass: HomeAssistant) -> None:
                """Raise a repair, now the weather data source has had time to start."""
                self._update_weather_source_issue()

            self._entry.async_on_unload(async_at_started(self.hass, started))

        if not self._weather_entity:
            return

        @callback
        def weather_changed(event: Event[EventStateChangedData]) -> None:
            """Work out the value again if the condition or cloud coverage changed."""
            new_state: State | None = event.data["new_state"]
            old_state: State | None = event.data["old_state"]
            if (
                not old_state
                or not new_state
                or new_state.state != old_state.state
                or new_state.attributes.get(ATTR_WEATHER_CLOUD_COVERAGE)
                != old_state.attributes.get(ATTR_WEATHER_CLOUD_COVERAGE)
            ):
                self._get_divisor_from_weather_data(new_state)
                self.async_set_updated_data(self._calculate())

        self._entry.async_on_unload(
            async_track_state_change_event(
                self.hass, self._weather_entity, weather_changed
            )
        )

    @callback
    def async_stop(self) -> None:
        """Delete the repair, if any: it's raised again when needed."""
        async_set_weather_source_issue(self.hass, self._entry.entry_id, None)

    def diagnostics(self) -> dict[str, Any]:
        """Return how the value was worked out, for diagnostics."""
        since = self._weather_unavailable_since
        return {
            "illuminance": self.data.value,
            "weather": self.data.weather,
            "divisor": self.data.divisor,
            "weather_unavailable_since": since.isoformat() if since else None,
        }

    async def _async_update_data(self) -> Illuminance:
        """Work out the value at the update period."""
        return self._calculate()

    def _calculate(self) -> Illuminance:
        """Work out the value, and raise or delete the repair."""
        self._update_weather_source_issue()
        now = dt_util.utcnow().replace(microsecond=0)
        elevation: float = astral.sun.elevation(get_astral_observer(self.hass), now)
        sunny = _illuminance(elevation)
        value = sunny / self._divisor
        _LOGGER.debug(
            "%s: Updating %s -> %s / %s = %s",
            self.name,
            self._weather,
            sunny,
            self._divisor,
            value,
        )
        return Illuminance(value, self._weather, self._divisor)

    def _get_divisor_from_weather_data(self, entity_state: State | None) -> None:
        """Get weather data from input entity."""

        # Use fallback unless divisor can be successfully determined from weather data.
        self._weather = "without weather data"
        self._divisor = self._fallback

        if not self._weather_entity:
            return

        condition = entity_state.state if entity_state else None
        if condition in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            condition = None

        if not condition:
            if self._weather_unavailable_since is None:
                self._weather_unavailable_since = dt_util.utcnow()
            # While Home Assistant starts, the weather integration may not have
            # been set up yet.
            if self.hass.is_running:
                self._log_problem("Weather data not available")
            return
        self._weather_unavailable_since = None

        # A sensor can report the cloud coverage percentage as its state.
        if (cloud := _cloud_coverage(condition)) is not None:
            self._weather = f"({round(cloud)}%)"
            self._divisor = 10 ** (cloud / 100)
            self._log_problem(None)
            return

        problem = self._get_divisor_from_condition(condition)
        self._log_problem(problem)

        # A weather entity's cloud coverage is more precise than its condition,
        # but the condition also reflects fog, rain and storms: use whichever is
        # darker.
        assert entity_state
        cloud = _cloud_coverage(
            entity_state.attributes.get(ATTR_WEATHER_CLOUD_COVERAGE)
        )
        if cloud is None:
            return
        cloud_divisor = 10 ** (cloud / 100)
        if problem or cloud_divisor > self._divisor:
            self._weather = f"({condition}, {round(cloud)}%)"
            self._divisor = cloud_divisor

    def _log_problem(self, problem: str | None) -> None:
        """Log a problem with the weather data once, until it changes or is fixed."""
        if problem and problem != self._problem:
            _LOGGER.warning("%s: %s", self.name, problem)
        self._problem = problem

    def _update_weather_source_issue(self) -> None:
        """Raise a repair if the weather data source is missing or unavailable."""
        # While Home Assistant starts, the source may not have been set up yet.
        if not self._weather_entity or not self.hass.is_running:
            return

        if (since := self._weather_unavailable_since) is None:
            async_set_weather_source_issue(self.hass, self._entry.entry_id, None)
            return

        placeholders = {
            "name": self.name,
            "entity_id": self._weather_entity,
            "since": dt_util.as_local(since).strftime("%Y-%m-%d %H:%M"),
        }
        if self.hass.states.get(self._weather_entity) is None:
            key: str | None = WEATHER_SOURCE_MISSING
        elif dt_util.utcnow() - since >= ISSUE_AFTER:
            key = WEATHER_SOURCE_UNAVAILABLE
        else:
            key = None
        async_set_weather_source_issue(
            self.hass, self._entry.entry_id, key, placeholders
        )

    def _get_divisor_from_condition(self, condition: str) -> str | None:
        """Get divisor from a weather condition.

        Returns the problem, if the condition isn't one of the expected ones.
        """
        if (divisor := DIVISORS.get(condition)) is None:
            return f"Unexpected current condition: {condition}"
        self._weather = f"({condition})"
        self._divisor = divisor
        return None
