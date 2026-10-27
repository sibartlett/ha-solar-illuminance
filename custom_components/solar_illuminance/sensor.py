"""Solar Illuminance sensors: the estimated illuminance, and its irradiance."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import LIGHT_LUX, UnitOfIrradiance
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LUX_PER_WPSM
from .coordinator import SolarIlluminanceConfigEntry, SolarIlluminanceCoordinator

# The sensors are calculated locally, so their updates needn't be limited.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SolarIlluminanceSensorEntityDescription(SensorEntityDescription):
    """Solar Illuminance sensor entity description."""

    # The sensor's value, from the illuminance in lx.
    value_fn: Callable[[float], float]


# Without a name, each sensor is named after its device class.
SENSORS = (
    SolarIlluminanceSensorEntityDescription(
        key="illuminance",
        device_class=SensorDeviceClass.ILLUMINANCE,
        native_unit_of_measurement=LIGHT_LUX,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=round,
    ),
    SolarIlluminanceSensorEntityDescription(
        key="irradiance",
        device_class=SensorDeviceClass.IRRADIANCE,
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        entity_registry_enabled_default=False,
        value_fn=lambda illuminance: round(illuminance / LUX_PER_WPSM, 2),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarIlluminanceConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    async_add_entities(
        SolarIlluminanceSensor(entry.runtime_data, description)
        for description in SENSORS
    )


class SolarIlluminanceSensor(
    CoordinatorEntity[SolarIlluminanceCoordinator], SensorEntity
):
    """Solar Illuminance sensor."""

    entity_description: SolarIlluminanceSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolarIlluminanceCoordinator,
        description: SolarIlluminanceSensorEntityDescription,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        # The illuminance sensor keeps the unique ID it had as the only sensor.
        self._attr_unique_id = (
            entry.entry_id
            if description.key == "illuminance"
            else f"{entry.entry_id}_{description.key}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> float:
        """Return the sensor's value."""
        return self.entity_description.value_fn(self.coordinator.data.value)
