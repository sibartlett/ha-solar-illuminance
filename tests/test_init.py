"""Tests for setting up Solar Illuminance, from YAML and config entries."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER, ConfigEntryState
from homeassistant.const import SERVICE_RELOAD
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_illuminance import entry_updated
from custom_components.solar_illuminance.const import DOMAIN
from custom_components.solar_illuminance.sensor import LOC_ELEV

from .conftest import SetupEntry

GARDEN = {"unique_id": "garden", "name": "Garden", "mode": "simple"}
PATIO = {"unique_id": "patio", "name": "Patio"}


async def _reload(hass: HomeAssistant, config: dict[str, Any]) -> None:
    """Reload the YAML configuration, as if it now says config."""
    with patch("homeassistant.config.load_yaml_config_file", return_value=config):
        await hass.services.async_call(DOMAIN, SERVICE_RELOAD, blocking=True)
    await hass.async_block_till_done()


def _imported(hass: HomeAssistant) -> dict[str, str]:
    """Return the unique ID and title of each imported config entry."""
    return {
        entry.unique_id: entry.title
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.source == SOURCE_IMPORT
    }


@pytest.mark.usefixtures("noon")
async def test_yaml(hass: HomeAssistant) -> None:
    """Test sensors in YAML are imported as config entries."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [GARDEN, PATIO]})
    await hass.async_block_till_done()

    assert _imported(hass) == {"garden": "Garden", "patio": "Patio"}
    garden = hass.states.get("sensor.garden")
    assert garden is not None
    assert garden.state == "10000"
    assert hass.states.get("sensor.patio") is not None


@pytest.mark.usefixtures("noon")
async def test_reload(hass: HomeAssistant) -> None:
    """Test reloading YAML adds, updates and removes imported sensors only."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [GARDEN]})
    await hass.async_block_till_done()
    user = MockConfigEntry(domain=DOMAIN, source=SOURCE_USER)
    user.add_to_hass(hass)

    await _reload(hass, {DOMAIN: [GARDEN | {"name": "Front Garden"}, PATIO]})
    assert _imported(hass) == {"garden": "Front Garden", "patio": "Patio"}

    await _reload(hass, {DOMAIN: [PATIO]})
    assert _imported(hass) == {"patio": "Patio"}

    await _reload(hass, {})
    assert _imported(hass) == {}
    assert hass.config_entries.async_get_entry(user.entry_id) is not None


async def test_location_changes(hass: HomeAssistant) -> None:
    """Test the sun's position follows Home Assistant's location."""
    assert await async_setup_component(hass, DOMAIN, {})
    assert hass.data[LOC_ELEV].latitude == hass.config.latitude

    await hass.config.async_update(latitude=51.5, longitude=-0.1)
    await hass.async_block_till_done()

    assert hass.data[LOC_ELEV].latitude == 51.5
    assert hass.data[LOC_ELEV].longitude == -0.1


@pytest.mark.usefixtures("noon")
async def test_unload(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test unloading a config entry."""
    entry = await setup_entry()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_update_while_unrecoverable(hass: HomeAssistant) -> None:
    """Test an entry updated while it can't be reloaded isn't reloaded."""
    entry = MagicMock(state=ConfigEntryState.SETUP_IN_PROGRESS)
    with patch.object(hass.config_entries, "async_reload", AsyncMock()) as async_reload:
        await entry_updated(hass, entry)

    async_reload.assert_not_called()
