"""Tests for the Solar Illuminance config and options flows."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.solar_illuminance.const import CONF_FALLBACK, DOMAIN

from .conftest import ENTITY_ID, WEATHER_ENTITY_ID, SetupEntry


@pytest.mark.usefixtures("noon")
async def test_user_flow(hass: HomeAssistant) -> None:
    """Test setting up a sensor from the UI."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "name"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NAME: "Garden"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "options"

    options = {
        CONF_SCAN_INTERVAL: 2.5,
        CONF_ENTITY_ID: WEATHER_ENTITY_ID,
        CONF_FALLBACK: 3,
    }
    result = await hass.config_entries.flow.async_configure(result["flow_id"], options)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Garden"
    assert result["data"] == {}
    assert result["options"] == options
    assert hass.states.get("sensor.garden_illuminance") is not None


@pytest.mark.usefixtures("noon")
async def test_options_flow(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test changing a sensor's options reloads it."""
    entry = await setup_entry(entity_id=WEATHER_ENTITY_ID, fallback=3)
    # Without weather data, the divider is used.
    assert hass.states.get(ENTITY_ID).state == "40778"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "options"
    schema = result["data_schema"].schema
    suggested = {
        str(key): key.description["suggested_value"]
        for key in schema
        if key.description
    }
    assert suggested == {
        CONF_SCAN_INTERVAL: 5,
        CONF_ENTITY_ID: WEATHER_ENTITY_ID,
        CONF_FALLBACK: 3,
    }

    options = {CONF_SCAN_INTERVAL: 1}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == options
    # Without a weather data source, the default divider is 1.
    assert hass.states.get(ENTITY_ID).state == "122334"
