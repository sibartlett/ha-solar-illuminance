"""Tests for the repairs about a sensor's weather data source."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import ATTR_ATTRIBUTION, STATE_UNAVAILABLE
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import issue_registry as ir
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.solar_illuminance.const import DOMAIN

from .conftest import ENTRY_ID, WEATHER_ENTITY_ID, SetupEntry

MISSING = f"weather_source_missing_{ENTRY_ID}"
UNAVAILABLE = f"weather_source_unavailable_{ENTRY_ID}"
SUNNY = ("sunny", {ATTR_ATTRIBUTION: "Met.no"})


def _issues(issue_registry: ir.IssueRegistry) -> dict[str, dict[str, str] | None]:
    """Return the integration's issues, and their placeholders."""
    return {
        issue_id: issue.translation_placeholders
        for (domain, issue_id), issue in issue_registry.issues.items()
        if domain == DOMAIN
    }


async def _wait(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, minutes: float
) -> None:
    """Let time pass, updating the sensor at its 5 minute scan interval."""
    for _ in range(int(minutes // 5)):
        freezer.tick(timedelta(minutes=5))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()


@pytest.mark.usefixtures("noon")
async def test_missing(
    hass: HomeAssistant, setup_entry: SetupEntry, issue_registry: ir.IssueRegistry
) -> None:
    """Test a weather data source that doesn't exist has a repair at once."""
    await setup_entry(title="Garden", entity_id=WEATHER_ENTITY_ID)

    assert _issues(issue_registry) == {
        MISSING: {
            "name": "Garden",
            "entity_id": WEATHER_ENTITY_ID,
            "since": "2026-06-21 12:50",
        }
    }

    hass.states.async_set(WEATHER_ENTITY_ID, *SUNNY)
    await hass.async_block_till_done()
    assert _issues(issue_registry) == {}


@pytest.mark.usefixtures("noon")
async def test_deleted(
    hass: HomeAssistant, setup_entry: SetupEntry, issue_registry: ir.IssueRegistry
) -> None:
    """Test deleting the weather data source raises a repair."""
    hass.states.async_set(WEATHER_ENTITY_ID, *SUNNY)
    await setup_entry(entity_id=WEATHER_ENTITY_ID)
    assert _issues(issue_registry) == {}

    hass.states.async_remove(WEATHER_ENTITY_ID)
    await hass.async_block_till_done()

    assert list(_issues(issue_registry)) == [MISSING]


async def test_unavailable(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    issue_registry: ir.IssueRegistry,
    noon: FrozenDateTimeFactory,
) -> None:
    """Test a repair is raised once the weather is unavailable for an hour."""
    hass.states.async_set(WEATHER_ENTITY_ID, *SUNNY)
    await setup_entry(title="Garden", entity_id=WEATHER_ENTITY_ID)

    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    await _wait(hass, noon, 55)
    assert _issues(issue_registry) == {}

    await _wait(hass, noon, 5)
    assert _issues(issue_registry) == {
        UNAVAILABLE: {
            "name": "Garden",
            "entity_id": WEATHER_ENTITY_ID,
            "since": "2026-06-21 12:50",
        }
    }

    hass.states.async_set(WEATHER_ENTITY_ID, *SUNNY)
    await hass.async_block_till_done()
    assert _issues(issue_registry) == {}


async def test_while_starting(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    issue_registry: ir.IssueRegistry,
    noon: FrozenDateTimeFactory,
) -> None:
    """Test there's no repair while Home Assistant starts."""
    hass.set_state(CoreState.not_running)
    await setup_entry(entity_id=WEATHER_ENTITY_ID)
    assert _issues(issue_registry) == {}

    # Once started, the sensor's next update raises it.
    hass.set_state(CoreState.running)
    await _wait(hass, noon, 5)
    assert list(_issues(issue_registry)) == [MISSING]


@pytest.mark.usefixtures("noon")
async def test_unload(
    hass: HomeAssistant, setup_entry: SetupEntry, issue_registry: ir.IssueRegistry
) -> None:
    """Test unloading a sensor deletes its repair."""
    entry = await setup_entry(entity_id=WEATHER_ENTITY_ID)
    assert list(_issues(issue_registry)) == [MISSING]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert _issues(issue_registry) == {}


@pytest.mark.usefixtures("noon")
async def test_no_weather_entity(
    hass: HomeAssistant, setup_entry: SetupEntry, issue_registry: ir.IssueRegistry
) -> None:
    """Test a sensor without a weather data source has no repair."""
    await setup_entry()

    assert _issues(issue_registry) == {}
