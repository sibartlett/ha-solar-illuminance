"""Snapshots of the entities the integration creates.

Update them with `pytest --snapshot-update`, and review the diff.
"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import snapshot_platform
from syrupy.assertion import SnapshotAssertion

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
