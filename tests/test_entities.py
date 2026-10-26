"""Snapshots of the entities the integration creates.

Update them with `pytest --snapshot-update`, and review the diff.
"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import snapshot_platform
from syrupy.assertion import SnapshotAssertion

from custom_components.solar_illuminance.const import DOMAIN

from .conftest import SetupEntry


@pytest.mark.usefixtures("noon")
@pytest.mark.parametrize("mode", ["normal", "irradiance", "simple"])
async def test_entities(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mode: str,
) -> None:
    """Test the sensor in each mode."""
    entry = await setup_entry(mode=mode)

    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)


@pytest.mark.usefixtures("noon")
async def test_device(
    hass: HomeAssistant,
    setup_entry: SetupEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test each sensor has a service device named after it.

    Not a snapshot: the device registry's fields differ between the Home
    Assistant versions tested.
    """
    entry = await setup_entry(title="Garden")

    [device] = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert device.name == "Garden"
    assert device.entry_type is dr.DeviceEntryType.SERVICE
    assert hass.states.get("sensor.garden") is not None
