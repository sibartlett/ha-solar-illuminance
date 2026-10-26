"""Tests for setting up Solar Illuminance."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.solar_illuminance import entry_updated
from custom_components.solar_illuminance.const import DOMAIN

from .conftest import ENTITY_ID, SetupEntry


@pytest.mark.usefixtures("noon")
async def test_yaml_not_supported(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test YAML configuration is reported, not set up."""
    assert await async_setup_component(hass, DOMAIN, {DOMAIN: [{"name": "Garden"}]})
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN) == []
    assert "does not support YAML setup" in caplog.text


async def test_location_changes(
    hass: HomeAssistant, setup_entry: SetupEntry, noon: FrozenDateTimeFactory
) -> None:
    """Test the sun's position follows Home Assistant's location."""
    await setup_entry()
    assert hass.states.get(ENTITY_ID).state == "122334"

    # In London, the sun is about to set.
    await hass.config.async_update(latitude=51.5, longitude=-0.1)
    noon.tick(timedelta(minutes=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert float(hass.states.get(ENTITY_ID).state) < 10000


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


@pytest.mark.usefixtures("noon")
async def test_rename(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test renaming a config entry renames its sensor."""
    entry = await setup_entry(title="Garden")

    hass.config_entries.async_update_entry(entry, title="Back Garden")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.garden")
    assert state is not None
    assert state.name == "Back Garden"
