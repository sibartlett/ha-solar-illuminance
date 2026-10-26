"""Tests for the Solar Illuminance config and options flows."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ENTITY_ID,
    CONF_MODE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    UnitOfIrradiance,
)
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
        CONF_MODE: "simple",
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
    assert hass.states.get("sensor.garden") is not None


@pytest.mark.usefixtures("noon")
async def test_options_flow(hass: HomeAssistant, setup_entry: SetupEntry) -> None:
    """Test changing a sensor's options reloads it."""
    entry = await setup_entry(entity_id=WEATHER_ENTITY_ID, fallback=3)

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
        CONF_MODE: "normal",
        CONF_SCAN_INTERVAL: 5,
        CONF_ENTITY_ID: WEATHER_ENTITY_ID,
        CONF_FALLBACK: 3,
    }

    options = {CONF_MODE: "irradiance", CONF_SCAN_INTERVAL: 1}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], options
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == options
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert (
        state.attributes[ATTR_UNIT_OF_MEASUREMENT]
        == UnitOfIrradiance.WATTS_PER_SQUARE_METER
    )
