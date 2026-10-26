"""Tests for Solar Illuminance diagnostics.

Update the snapshots with `pytest --snapshot-update`, and review the diff.
"""

from homeassistant.const import ATTR_ATTRIBUTION, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
import pytest
from syrupy.assertion import SnapshotAssertion

from custom_components.solar_illuminance.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import WEATHER_ENTITY_ID, SetupEntry


@pytest.mark.usefixtures("noon")
async def test_diagnostics(
    hass: HomeAssistant, setup_entry: SetupEntry, snapshot: SnapshotAssertion
) -> None:
    """Test diagnostics include the weather data source and the divisor."""
    hass.states.async_set(
        WEATHER_ENTITY_ID, "cloudy", {ATTR_ATTRIBUTION: "Met.no", "cloud_coverage": 80}
    )
    entry = await setup_entry(entity_id=WEATHER_ENTITY_ID)

    assert await async_get_config_entry_diagnostics(hass, entry) == snapshot


@pytest.mark.usefixtures("noon")
async def test_diagnostics_unavailable(
    hass: HomeAssistant, setup_entry: SetupEntry, snapshot: SnapshotAssertion
) -> None:
    """Test diagnostics while the weather data source is unavailable."""
    hass.states.async_set(WEATHER_ENTITY_ID, STATE_UNAVAILABLE)
    entry = await setup_entry(entity_id=WEATHER_ENTITY_ID)

    assert await async_get_config_entry_diagnostics(hass, entry) == snapshot


@pytest.mark.usefixtures("noon")
async def test_diagnostics_no_weather_entity(
    hass: HomeAssistant, setup_entry: SetupEntry, snapshot: SnapshotAssertion
) -> None:
    """Test diagnostics for a sensor without a weather data source."""
    entry = await setup_entry()

    assert await async_get_config_entry_diagnostics(hass, entry) == snapshot


@pytest.mark.usefixtures("noon")
async def test_diagnostics_missing(
    hass: HomeAssistant, setup_entry: SetupEntry
) -> None:
    """Test diagnostics when the weather data source doesn't exist."""
    entry = await setup_entry(entity_id=WEATHER_ENTITY_ID)

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["options"]["entity_id"] == WEATHER_ENTITY_ID
    assert diagnostics["weather_source"] is None
