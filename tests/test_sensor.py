"""Tests for the Solar Illuminance sensor."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.weather.const import ATTR_WEATHER_CLOUD_COVERAGE
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfIrradiance,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.solar_illuminance.coordinator import _illuminance

from .conftest import (
    ENTITY_ID,
    IRRADIANCE_ENTITY_ID,
    MIDNIGHT,
    SUNRISE,
    WEATHER_ENTITY_ID,
    SetupEntry,
)

CLOUD_ENTITY_ID = "sensor.cloud_coverage"
# The illuminance at solar noon, without weather.
NOON_LUX = 122334


def _state(hass: HomeAssistant, entity_id: str = ENTITY_ID) -> float:
    """Return a sensor's state as a number."""
    state = hass.states.get(entity_id)
    assert state is not None
    return float(state.state)


def _divisor(hass: HomeAssistant) -> float:
    """Return the divisor the weather gave, from the illuminance at noon."""
    return NOON_LUX / _state(hass)


@pytest.mark.parametrize(
    ("elevation", "illuminance"),
    [(90, 124879), (45, 81016), (10, 11493), (0, 757), (-5, 9)],
)
def test_illuminance(elevation: float, illuminance: float) -> None:
    """Test the US Naval Observatory illuminance algorithm."""
    assert _illuminance(elevation) == pytest.approx(illuminance, abs=0.5)


@pytest.mark.usefixtures("noon")
async def test_illuminance_sensor(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test the illuminance at solar noon, without weather data."""
    await setup_entry()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == str(NOON_LUX)
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX


@pytest.mark.usefixtures("noon", "enable_irradiance")
async def test_irradiance_sensor(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test irradiance is the illuminance divided by 120 lx per W/m²."""
    await setup_entry()

    state = hass.states.get(IRRADIANCE_ENTITY_ID)
    assert state is not None
    assert state.state == "1019.45"
    assert (
        state.attributes[ATTR_UNIT_OF_MEASUREMENT]
        == UnitOfIrradiance.WATTS_PER_SQUARE_METER
    )


@pytest.mark.parametrize(
    ("now", "illuminance"),
    [(MIDNIGHT, 0), (SUNRISE, 603)],
    ids=["midnight", "sunrise"],
)
async def test_through_the_day(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    freezer: FrozenDateTimeFactory,
    now: object,
    illuminance: float,
) -> None:
    """Test the illuminance follows the sun's elevation."""
    freezer.move_to(now)
    await setup_entry()

    assert _state(hass) == pytest.approx(illuminance, abs=20)


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("condition", "attribution", "divisor"),
    [
        ("sunny", "Met.no", 1),
        ("clear-night", "Met.no", 1),
        ("windy", "Met.no", 1),
        ("partlycloudy", "Met.no", 2),
        ("windy-variant", "Met.no", 2),
        ("cloudy", "Met.no", 5),
        ("fog", "Met.no", 5),
        ("rainy", "Met.no", 5),
        ("lightning", "Met.no", 10),
        ("pouring", "Met.no", 10),
        # Some weather sources have conditions of their own, which are
        # recognised whatever the source.
        ("mostlycloudy", "Data provided by AccuWeather", 3),
        ("mostlycloudy", None, 3),
        ("snowy-heavy", "Ecobee weather provided by KSAN", 10),
        ("tornado", None, 5),
        ("hazy", "Met.no", 2),
        # Without an attribution, the standard conditions are used.
        ("cloudy", None, 5),
    ],
)
async def test_weather_condition(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    condition: str,
    attribution: str | None,
    divisor: float,
) -> None:
    """Test the illuminance is divided according to the weather condition."""
    attributes = {ATTR_ATTRIBUTION: attribution} if attribution else {}
    hass.states.async_set(WEATHER_ENTITY_ID, condition, attributes)
    await setup_entry(entity_id=WEATHER_ENTITY_ID)

    assert _divisor(hass) == pytest.approx(divisor, rel=1e-4)


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("condition", "cloud_coverage", "divisor"),
    [
        # Whichever is darker is used: here, the cloud coverage.
        ("sunny", 0, 1),
        ("sunny", 80, 10**0.8),
        ("partlycloudy", 50, 10**0.5),
        ("cloudy", 100, 10),
        ("cloudy", 150, 10),
        # Here, the condition, which reflects fog and rain.
        ("cloudy", 50, 5),
        ("fog", 10, 5),
        ("pouring", 20, 10),
        # Without a valid cloud coverage, the condition is used.
        ("cloudy", None, 5),
        ("cloudy", "lots", 5),
        # With an unexpected condition, the cloud coverage is used.
        ("bogus", 50, 10**0.5),
    ],
)
async def test_weather_cloud_coverage(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    condition: str,
    cloud_coverage: float | str | None,
    divisor: float,
) -> None:
    """Test the darker of a weather entity's cloud coverage and condition is used."""
    hass.states.async_set(
        WEATHER_ENTITY_ID,
        condition,
        {ATTR_ATTRIBUTION: "Met.no", ATTR_WEATHER_CLOUD_COVERAGE: cloud_coverage},
    )
    await setup_entry(entity_id=WEATHER_ENTITY_ID)

    assert _divisor(hass) == pytest.approx(divisor, rel=1e-4)


@pytest.mark.usefixtures("noon")
async def test_weather_cloud_coverage_changes(
    hass: HomeAssistant, setup_entry: SetupEntry
) -> None:
    """Test the sensor updates when only the cloud coverage changes."""
    attributes = {ATTR_ATTRIBUTION: "Met.no"}
    hass.states.async_set(
        WEATHER_ENTITY_ID, "sunny", attributes | {ATTR_WEATHER_CLOUD_COVERAGE: 0}
    )
    await setup_entry(entity_id=WEATHER_ENTITY_ID)
    assert _divisor(hass) == pytest.approx(1, rel=1e-4)

    hass.states.async_set(
        WEATHER_ENTITY_ID, "sunny", attributes | {ATTR_WEATHER_CLOUD_COVERAGE: 100}
    )
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(10, rel=1e-4)


@pytest.mark.usefixtures("noon")
async def test_unexpected_condition(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test an unknown condition uses the fallback divisor."""
    hass.states.async_set(WEATHER_ENTITY_ID, "bogus", {ATTR_ATTRIBUTION: "Met.no"})
    await setup_entry(entity_id=WEATHER_ENTITY_ID)

    # The default fallback with a weather entity is 10.
    assert _divisor(hass) == pytest.approx(10, rel=1e-4)
    assert caplog.text.count("Unexpected current condition: bogus") == 1

    # It's logged once, until the condition changes or is fixed.
    hass.states.async_set(
        WEATHER_ENTITY_ID, "bogus", {ATTR_ATTRIBUTION: "Met.no", "cloud_coverage": 50}
    )
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(10**0.5, rel=1e-4)
    assert caplog.text.count("Unexpected current condition: bogus") == 1
    hass.states.async_set(WEATHER_ENTITY_ID, "sunny", {ATTR_ATTRIBUTION: "Met.no"})
    await hass.async_block_till_done()
    hass.states.async_set(WEATHER_ENTITY_ID, "bogus", {ATTR_ATTRIBUTION: "Met.no"})
    await hass.async_block_till_done()
    assert caplog.text.count("Unexpected current condition: bogus") == 2
    hass.states.async_set(WEATHER_ENTITY_ID, "weird", {ATTR_ATTRIBUTION: "Met.no"})
    await hass.async_block_till_done()
    assert "Unexpected current condition: weird" in caplog.text


@pytest.mark.usefixtures("noon")
async def test_weather_changes(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test the sensor updates as soon as the weather changes."""
    hass.states.async_set(WEATHER_ENTITY_ID, "sunny", {ATTR_ATTRIBUTION: "Met.no"})
    await setup_entry(entity_id=WEATHER_ENTITY_ID)
    assert _divisor(hass) == pytest.approx(1, rel=1e-4)

    hass.states.async_set(WEATHER_ENTITY_ID, "cloudy", {ATTR_ATTRIBUTION: "Met.no"})
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(5, rel=1e-4)

    # A change to only the attributes doesn't need an update.
    hass.states.async_set(WEATHER_ENTITY_ID, "cloudy", {ATTR_ATTRIBUTION: "Other"})
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(5, rel=1e-4)


@pytest.mark.usefixtures("noon")
async def test_weather_unavailable(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the fallback is used, with one warning, while there's no weather."""
    hass.states.async_set(WEATHER_ENTITY_ID, "sunny", {ATTR_ATTRIBUTION: "Met.no"})
    await setup_entry(entity_id=WEATHER_ENTITY_ID, fallback=4)

    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(4, rel=1e-4)

    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNKNOWN)
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(4, rel=1e-4)
    assert caplog.text.count("Weather data not available") == 1

    hass.states.async_set(WEATHER_ENTITY_ID, "sunny", {ATTR_ATTRIBUTION: "Met.no"})
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(1, rel=1e-4)


@pytest.mark.usefixtures("noon")
async def test_weather_entity_missing(
    hass: HomeAssistant, setup_entry: SetupEntry
) -> None:
    """Test a weather entity that doesn't exist."""
    await setup_entry(entity_id=WEATHER_ENTITY_ID)

    assert _divisor(hass) == pytest.approx(10, rel=1e-4)

    # Once it exists, it's assumed to use the standard conditions.
    hass.states.async_set(WEATHER_ENTITY_ID, "partlycloudy")
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(2, rel=1e-4)


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("cloud_coverage", "divisor"),
    [("0", 1), ("50", 10**0.5), ("100", 10), ("150", 10), ("-10", 1)],
)
async def test_cloud_coverage(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    cloud_coverage: str,
    divisor: float,
) -> None:
    """Test the illuminance is divided according to the cloud coverage."""
    hass.states.async_set(CLOUD_ENTITY_ID, cloud_coverage)
    await setup_entry(entity_id=CLOUD_ENTITY_ID)

    assert _divisor(hass) == pytest.approx(divisor, rel=1e-4)


@pytest.mark.usefixtures("noon")
async def test_cloud_coverage_not_a_number(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test a cloud coverage sensor that stops reporting a number."""
    hass.states.async_set(CLOUD_ENTITY_ID, "0")
    await setup_entry(entity_id=CLOUD_ENTITY_ID)

    hass.states.async_set(CLOUD_ENTITY_ID, "lots")
    await hass.async_block_till_done()

    # It's taken to be a condition, and not one the sensor knows.
    assert _divisor(hass) == pytest.approx(10, rel=1e-4)
    assert "Unexpected current condition: lots" in caplog.text

    hass.states.async_set(CLOUD_ENTITY_ID, "50")
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(10**0.5, rel=1e-4)

    # Fixed, so it's logged again if it happens again.
    hass.states.async_set(CLOUD_ENTITY_ID, "lots")
    await hass.async_block_till_done()
    assert caplog.text.count("Unexpected current condition: lots") == 2


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("options", "divisor"),
    [({}, 1), ({"fallback": 2}, 2)],
    ids=["default", "fallback"],
)
async def test_no_weather_entity(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    options: dict[str, float],
    divisor: float,
) -> None:
    """Test the fallback divisor is used without a weather entity."""
    await setup_entry(**options)

    assert _divisor(hass) == pytest.approx(divisor, rel=1e-4)


@pytest.mark.usefixtures("noon")
async def test_before_start(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the sensor while the weather integration is still starting."""
    hass.set_state(CoreState.not_running)
    await setup_entry(entity_id=WEATHER_ENTITY_ID)

    # The fallback is used, without a warning, until the weather is available.
    assert _divisor(hass) == pytest.approx(10, rel=1e-4)
    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(10, rel=1e-4)
    assert "Weather data not available" not in caplog.text

    hass.states.async_set(WEATHER_ENTITY_ID, "cloudy")
    await hass.async_block_till_done()
    assert _divisor(hass) == pytest.approx(5, rel=1e-4)


async def test_scan_interval(
    hass: HomeAssistant, setup_entry: SetupEntry, freezer: FrozenDateTimeFactory
) -> None:
    """Test the sensor updates at the configured interval."""
    freezer.move_to(SUNRISE)
    await setup_entry(scan_interval=1)
    before = _state(hass)

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert _state(hass) > before


async def test_update_entity(
    hass: HomeAssistant, setup_entry: SetupEntry, freezer: FrozenDateTimeFactory
) -> None:
    """Test the homeassistant.update_entity action recalculates the value."""
    assert await async_setup_component(hass, "homeassistant", {})
    freezer.move_to(SUNRISE)
    await setup_entry(scan_interval=60)
    before = _state(hass)

    freezer.tick(timedelta(minutes=1))
    await hass.services.async_call(
        "homeassistant", "update_entity", {"entity_id": ENTITY_ID}, blocking=True
    )

    assert _state(hass) > before
