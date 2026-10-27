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
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.solar_illuminance.sensor import _illuminance

from .conftest import (
    ENTITY_ID,
    MIDNIGHT,
    NOON,
    SUNRISE,
    SUNSET,
    WEATHER_ENTITY_ID,
    SetupEntry,
)

CLOUD_ENTITY_ID = "sensor.cloud_coverage"


def _state(hass: HomeAssistant) -> float:
    """Return the sensor's state as a number."""
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    return float(state.state)


@pytest.mark.parametrize(
    ("elevation", "illuminance"),
    [(90, 124879), (45, 81016), (10, 11493), (0, 757), (-5, 9)],
)
def test_illuminance(elevation: float, illuminance: float) -> None:
    """Test the US Naval Observatory illuminance algorithm."""
    assert _illuminance(elevation) == pytest.approx(illuminance, abs=0.5)


@pytest.mark.usefixtures("noon")
async def test_normal_mode(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test the illuminance at solar noon, without weather data."""
    await setup_entry()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "122334"
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == LIGHT_LUX


@pytest.mark.usefixtures("noon")
async def test_irradiance_mode(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test irradiance is the illuminance divided by 120 lx per W/m²."""
    await setup_entry(mode="irradiance")

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "1019.45"
    assert (
        state.attributes[ATTR_UNIT_OF_MEASUREMENT]
        == UnitOfIrradiance.WATTS_PER_SQUARE_METER
    )


@pytest.mark.parametrize(
    ("now", "illuminance"),
    [
        (NOON, 10000),
        (MIDNIGHT, 10),
        # Ramps up over the hour from 20 minutes before sunrise, and down over
        # the hour to 20 minutes after sunset.
        (SUNRISE - timedelta(minutes=20), 0),
        (SUNRISE, 3333),
        (SUNRISE + timedelta(minutes=10), 5000),
        (SUNSET - timedelta(minutes=10), 5000),
        (SUNSET + timedelta(minutes=19), 167),
    ],
    ids=["noon", "midnight", "dawn", "sunrise", "morning", "evening", "dusk"],
)
async def test_simple_mode(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    freezer: FrozenDateTimeFactory,
    now: object,
    illuminance: float,
) -> None:
    """Test simple mode's illuminance through the day."""
    freezer.move_to(now)
    await setup_entry(mode="simple")

    assert _state(hass) == pytest.approx(illuminance, abs=5)


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("condition", "attribution", "illuminance"),
    [
        ("sunny", "Met.no", 10000),
        ("clear-night", "Met.no", 10000),
        ("windy", "Met.no", 10000),
        ("partlycloudy", "Met.no", 5000),
        ("windy-variant", "Met.no", 5000),
        ("cloudy", "Met.no", 2000),
        ("fog", "Met.no", 2000),
        ("rainy", "Met.no", 2000),
        ("lightning", "Met.no", 1000),
        ("pouring", "Met.no", 1000),
        # Some weather sources have conditions of their own, which are
        # recognised whatever the source.
        ("mostlycloudy", "Data provided by AccuWeather", 3333),
        ("mostlycloudy", None, 3333),
        ("snowy-heavy", "Ecobee weather provided by KSAN", 1000),
        ("tornado", None, 2000),
        ("hazy", "Met.no", 5000),
        # Without an attribution, the standard conditions are used.
        ("cloudy", None, 2000),
    ],
)
async def test_weather_condition(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    condition: str,
    attribution: str | None,
    illuminance: float,
) -> None:
    """Test the illuminance is divided according to the weather condition."""
    attributes = {ATTR_ATTRIBUTION: attribution} if attribution else {}
    hass.states.async_set(WEATHER_ENTITY_ID, condition, attributes)
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID)

    assert _state(hass) == illuminance


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("condition", "cloud_coverage", "illuminance"),
    [
        # Whichever is darker is used: here, the cloud coverage.
        ("sunny", 0, 10000),
        ("sunny", 80, 1585),
        ("partlycloudy", 50, 3162),
        ("cloudy", 100, 1000),
        ("cloudy", 150, 1000),
        # Here, the condition, which reflects fog and rain.
        ("cloudy", 50, 2000),
        ("fog", 10, 2000),
        ("pouring", 20, 1000),
        # Without a valid cloud coverage, the condition is used.
        ("cloudy", None, 2000),
        ("cloudy", "lots", 2000),
        # With an unexpected condition, the cloud coverage is used.
        ("bogus", 50, 3162),
    ],
)
async def test_weather_cloud_coverage(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    condition: str,
    cloud_coverage: float | str | None,
    illuminance: float,
) -> None:
    """Test the darker of a weather entity's cloud coverage and condition is used."""
    hass.states.async_set(
        WEATHER_ENTITY_ID,
        condition,
        {ATTR_ATTRIBUTION: "Met.no", ATTR_WEATHER_CLOUD_COVERAGE: cloud_coverage},
    )
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID)

    assert _state(hass) == illuminance


@pytest.mark.usefixtures("noon")
async def test_weather_cloud_coverage_changes(
    hass: HomeAssistant, setup_entry: SetupEntry
) -> None:
    """Test the sensor updates when only the cloud coverage changes."""
    attributes = {ATTR_ATTRIBUTION: "Met.no"}
    hass.states.async_set(
        WEATHER_ENTITY_ID, "sunny", attributes | {ATTR_WEATHER_CLOUD_COVERAGE: 0}
    )
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID)
    assert _state(hass) == 10000

    hass.states.async_set(
        WEATHER_ENTITY_ID, "sunny", attributes | {ATTR_WEATHER_CLOUD_COVERAGE: 100}
    )
    await hass.async_block_till_done()
    assert _state(hass) == 1000


@pytest.mark.usefixtures("noon")
async def test_unexpected_condition(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test an unknown condition uses the fallback divisor."""
    hass.states.async_set(WEATHER_ENTITY_ID, "bogus", {ATTR_ATTRIBUTION: "Met.no"})
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID)

    # The default fallback with a weather entity is 10.
    assert _state(hass) == 1000
    assert caplog.text.count("Unexpected current condition: bogus") == 1

    # It's logged once, until the condition changes or is fixed.
    hass.states.async_set(
        WEATHER_ENTITY_ID, "bogus", {ATTR_ATTRIBUTION: "Met.no", "cloud_coverage": 50}
    )
    await hass.async_block_till_done()
    assert _state(hass) == 3162
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
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID)
    assert _state(hass) == 10000

    hass.states.async_set(WEATHER_ENTITY_ID, "cloudy", {ATTR_ATTRIBUTION: "Met.no"})
    await hass.async_block_till_done()
    assert _state(hass) == 2000

    # A change to only the attributes doesn't need an update.
    hass.states.async_set(WEATHER_ENTITY_ID, "cloudy", {ATTR_ATTRIBUTION: "Other"})
    await hass.async_block_till_done()
    assert _state(hass) == 2000


@pytest.mark.usefixtures("noon")
async def test_weather_unavailable(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the fallback is used, with one warning, while there's no weather."""
    hass.states.async_set(WEATHER_ENTITY_ID, "sunny", {ATTR_ATTRIBUTION: "Met.no"})
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID, fallback=4)

    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert _state(hass) == 2500

    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNKNOWN)
    await hass.async_block_till_done()
    assert _state(hass) == 2500
    assert caplog.text.count("Weather data not available") == 1

    hass.states.async_set(WEATHER_ENTITY_ID, "sunny", {ATTR_ATTRIBUTION: "Met.no"})
    await hass.async_block_till_done()
    assert _state(hass) == 10000


@pytest.mark.usefixtures("noon")
async def test_weather_entity_missing(
    hass: HomeAssistant, setup_entry: SetupEntry
) -> None:
    """Test a weather entity that doesn't exist."""
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID)

    assert _state(hass) == 1000

    # Once it exists, it's assumed to use the standard conditions.
    hass.states.async_set(WEATHER_ENTITY_ID, "partlycloudy")
    await hass.async_block_till_done()
    assert _state(hass) == 5000


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("cloud_coverage", "illuminance"),
    [("0", 10000), ("50", 3162), ("100", 1000), ("150", 1000), ("-10", 10000)],
)
async def test_cloud_coverage(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    cloud_coverage: str,
    illuminance: float,
) -> None:
    """Test the illuminance is divided according to the cloud coverage."""
    hass.states.async_set(CLOUD_ENTITY_ID, cloud_coverage)
    await setup_entry(mode="simple", entity_id=CLOUD_ENTITY_ID)

    assert _state(hass) == illuminance


@pytest.mark.usefixtures("noon")
async def test_cloud_coverage_not_a_number(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test a cloud coverage sensor that stops reporting a number."""
    hass.states.async_set(CLOUD_ENTITY_ID, "0")
    await setup_entry(mode="simple", entity_id=CLOUD_ENTITY_ID)

    hass.states.async_set(CLOUD_ENTITY_ID, "lots")
    await hass.async_block_till_done()

    assert _state(hass) == 1000
    assert "Cloud coverage sensor state is not a number: lots" in caplog.text


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize(
    ("options", "illuminance"),
    [({}, 10000), ({"fallback": 2}, 5000)],
    ids=["default", "fallback"],
)
async def test_no_weather_entity(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    options: dict[str, float],
    illuminance: float,
) -> None:
    """Test the fallback divisor is used without a weather entity."""
    await setup_entry(mode="simple", **options)

    assert _state(hass) == illuminance


@pytest.mark.usefixtures("noon")
async def test_before_start(
    hass: HomeAssistant, setup_entry: SetupEntry, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the sensor while the weather integration is still starting."""
    hass.set_state(CoreState.not_running)
    await setup_entry(mode="simple", entity_id=WEATHER_ENTITY_ID)

    # The fallback is used, without a warning, until the weather is available.
    assert _state(hass) == 1000
    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert _state(hass) == 1000
    assert "Weather data not available" not in caplog.text

    hass.states.async_set(WEATHER_ENTITY_ID, "cloudy")
    await hass.async_block_till_done()
    assert _state(hass) == 2000


async def test_scan_interval(
    hass: HomeAssistant, setup_entry: SetupEntry, freezer: FrozenDateTimeFactory
) -> None:
    """Test the sensor updates at the configured interval."""
    freezer.move_to(SUNRISE)
    await setup_entry(mode="simple", scan_interval=1)
    before = _state(hass)

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert _state(hass) == pytest.approx(before + 10000 / 60, abs=1)
