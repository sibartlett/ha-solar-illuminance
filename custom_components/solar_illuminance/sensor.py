"""Solar Illuminance Sensor.

A Sensor platform that estimates outdoor illuminance from current weather conditions.
"""

from datetime import datetime, timedelta
from enum import StrEnum
import logging
from math import asin, cos, exp, radians, sin
from typing import Any

import astral.sun
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
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
    CONF_MODE,
    CONF_SCAN_INTERVAL,
    LIGHT_LUX,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfIrradiance,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.sun import get_astral_observer
import homeassistant.util.dt as dt_util

from .const import CONF_FALLBACK, DEFAULT_FALLBACK, DOMAIN, ISSUE_AFTER, LUX_PER_WPSM
from .issues import (
    WEATHER_SOURCE_MISSING,
    WEATHER_SOURCE_UNAVAILABLE,
    async_set_weather_source_issue,
)

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

_LOGGER = logging.getLogger(__name__)

# The sensor is calculated locally, so its updates needn't be limited.
PARALLEL_UPDATES = 0


class Mode(StrEnum):
    """Illuminance mode."""

    normal = "normal"
    simple = "simple"
    irradiance = "irradiance"


MODES = list(Mode)

_20_MIN = timedelta(minutes=20)
_40_MIN = timedelta(minutes=40)


ILLUMINANCE = SensorEntityDescription(
    key=DOMAIN,
    device_class=SensorDeviceClass.ILLUMINANCE,
    name=None,
    native_unit_of_measurement=LIGHT_LUX,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=0,
)
IRRADIANCE = SensorEntityDescription(
    key=DOMAIN,
    device_class=SensorDeviceClass.IRRADIANCE,
    name=None,
    native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=2,
)


type SolarIlluminanceConfigEntry = ConfigEntry[SolarIlluminanceSensor]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarIlluminanceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    # The sensor is kept for diagnostics.
    entry.runtime_data = SolarIlluminanceSensor(entry)
    async_add_entities([entry.runtime_data])


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


class SolarIlluminanceSensor(SensorEntity):
    """Solar Illuminance sensor."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _divisor: Num
    _weather: str | None = None
    # The problem with the weather data last logged, if it hasn't been fixed.
    _problem: str | None = None
    # When the weather data source stopped having weather data, if it has none.
    _weather_unavailable_since: datetime | None = None

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize sensor from the config entry's options."""
        options = entry.options
        self._weather_entity: str | None = options.get(CONF_ENTITY_ID)
        self._mode = Mode(options[CONF_MODE])
        self._fallback: float = options.get(
            CONF_FALLBACK, DEFAULT_FALLBACK if self._weather_entity else 1
        )
        self._scan_interval = timedelta(minutes=options[CONF_SCAN_INTERVAL])
        self._entry_id = entry.entry_id
        self._title = entry.title
        self.entity_description = (
            IRRADIANCE if self._mode is Mode.irradiance else ILLUMINANCE
        )
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        """Start updating, at the scan interval and when the weather changes."""
        self._get_divisor_from_weather_data(
            self.hass.states.get(self._weather_entity) if self._weather_entity else None
        )
        self._update_value()

        # A repair isn't raised while Home Assistant starts, so check as soon
        # as it has, rather than at the next update.
        if not self.hass.is_running:

            @callback
            def started(hass: HomeAssistant) -> None:
                """Raise a repair, now the weather data source has had time to start."""
                self._update_weather_source_issue()

            self.async_on_remove(async_at_started(self.hass, started))

        @callback
        def scheduled_update(now: datetime) -> None:
            """Update at the scan interval."""
            self._update_value()
            self.async_write_ha_state()

        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                scheduled_update,
                self._scan_interval,
            )
        )

        if not self._weather_entity:
            return

        @callback
        def sensor_state_listener(event: Event[EventStateChangedData]) -> None:
            """Process input entity state update."""
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
                self._update_value()
                self.async_write_ha_state()

        # When source entity changes check to see if we should update.
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._weather_entity, sensor_state_listener
            )
        )

    def diagnostics(self) -> dict[str, Any]:
        """Return how the sensor's value was worked out, for diagnostics."""
        since = self._weather_unavailable_since
        return {
            "entity_id": self.entity_id,
            "value": self.native_value,
            "weather": self._weather,
            "divisor": self._divisor,
            "weather_unavailable_since": since.isoformat() if since else None,
        }

    async def async_will_remove_from_hass(self) -> None:
        """Delete the sensor's repair, if any: it's raised again when needed."""
        async_set_weather_source_issue(self.hass, self._entry_id, None)

    async def async_update(self) -> None:
        """Update the value when asked to, e.g. by homeassistant.update_entity."""
        self._update_value()

    def _update_value(self) -> None:
        """Calculate the value, and raise or delete the repair."""
        self._update_weather_source_issue()

        now = dt_util.utcnow().replace(microsecond=0)
        if (value := self._calculate_illuminance(now)) is None:
            # It's nighttime in simple mode: for historic reasons, the value is 10.
            _LOGGER.debug("%s: Updating -> 10", self.entity_id)
            self._attr_native_value = 10
            return

        if self._mode is Mode.irradiance:
            value /= LUX_PER_WPSM
            digits = 2
        else:
            digits = None

        # Calculate final value.

        self._attr_native_value = round(value / self._divisor, digits)
        _LOGGER.debug(
            "%s: Updating %s -> %s / %s = %s",
            self.entity_id,
            self._weather,
            value,
            self._divisor,
            self._attr_native_value,
        )

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
            _LOGGER.warning("%s: %s", self.entity_id, problem)
        self._problem = problem

    def _update_weather_source_issue(self) -> None:
        """Raise a repair if the weather data source is missing or unavailable."""
        # While Home Assistant starts, the source may not have been set up yet.
        if not self._weather_entity or not self.hass.is_running:
            return

        if (since := self._weather_unavailable_since) is None:
            async_set_weather_source_issue(self.hass, self._entry_id, None)
            return

        placeholders = {
            "name": self._title,
            "entity_id": self._weather_entity,
            "since": dt_util.as_local(since).strftime("%Y-%m-%d %H:%M"),
        }
        if self.hass.states.get(self._weather_entity) is None:
            key: str | None = WEATHER_SOURCE_MISSING
        elif dt_util.utcnow() - since >= ISSUE_AFTER:
            key = WEATHER_SOURCE_UNAVAILABLE
        else:
            key = None
        async_set_weather_source_issue(self.hass, self._entry_id, key, placeholders)

    def _get_divisor_from_condition(self, condition: str) -> str | None:
        """Get divisor from a weather condition.

        Returns the problem, if the condition isn't one of the expected ones.
        """
        if (divisor := DIVISORS.get(condition)) is None:
            return f"Unexpected current condition: {condition}"
        self._weather = f"({condition})"
        self._divisor = divisor
        return None

    def _calculate_illuminance(self, now: datetime) -> Num | None:
        """Calculate sunny illuminance, or None if it's nighttime in simple mode."""
        if self._mode is not Mode.simple:
            elevation: float = astral.sun.elevation(get_astral_observer(self.hass), now)
            return _illuminance(elevation)

        sun_factor = self._sun_factor(now)

        if sun_factor == 0:
            return None
        return 10000 * sun_factor

    def _sun_factor(self, now: datetime) -> Num:
        """Calculate sun factor."""
        now_date = dt_util.as_local(now).date()

        # Worked out each time, so they follow changes to Home Assistant's
        # location and time zone.
        observer = get_astral_observer(self.hass)
        sunrise: datetime = astral.sun.sunrise(observer, now_date)
        sunset: datetime = astral.sun.sunset(observer, now_date)
        sunrise_begin = sunrise - _20_MIN
        sunrise_end = sunrise + _40_MIN
        sunset_begin = sunset - _40_MIN
        sunset_end = sunset + _20_MIN

        if sunrise_end < now < sunset_begin:
            # Daytime
            return 1
        if now < sunrise_begin or sunset_end < now:
            # Nighttime
            return 0
        if now <= sunrise_end:
            # Sunrise
            return (now - sunrise_begin).total_seconds() / (60 * 60)
        # Sunset
        return (sunset_end - now).total_seconds() / (60 * 60)
