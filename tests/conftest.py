"""Fixtures for the Solar Illuminance tests."""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import CONF_MODE, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from custom_components.solar_illuminance.const import DOMAIN

# The test Home Assistant instance is in San Diego (US/Pacific). Solar noon
# there on the June solstice is about 12:50 PDT.
NOON = datetime.fromisoformat("2026-06-21T19:50:00+00:00")
MIDNIGHT = datetime.fromisoformat("2026-06-21T07:50:00+00:00")
# Sunrise and sunset there that day, to the second.
SUNRISE = datetime.fromisoformat("2026-06-21T12:41:23+00:00")
SUNSET = datetime.fromisoformat("2026-06-22T03:00:13+00:00")

# A fixed ID, as it is also the sensor's unique ID, which snapshots include.
ENTRY_ID = "01K8GQ5M0Z6Y3W2V1T9S8R7Q6P"
ENTITY_ID = "sensor.solar_illuminance"
WEATHER_ENTITY_ID = "weather.home"

type SetupEntry = Callable[..., Awaitable[MockConfigEntry]]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom_components."""


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Snapshot with Home Assistant's extension, which hides random IDs."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def noon(freezer: FrozenDateTimeFactory) -> FrozenDateTimeFactory:
    """Freeze time at solar noon."""
    freezer.move_to(NOON)
    return freezer


@pytest.fixture
def setup_entry(hass: HomeAssistant) -> SetupEntry:
    """Return a function that sets up a config entry with the given options."""

    async def _setup(
        *, title: str = "Solar Illuminance", **options: Any
    ) -> MockConfigEntry:
        entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id=ENTRY_ID,
            title=title,
            options={CONF_MODE: "normal", CONF_SCAN_INTERVAL: 5} | options,
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup
