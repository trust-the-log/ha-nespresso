"""Sensor platform for Nespresso integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NespressoCoordinator
from .api import NespressoClient
from .const import DOMAIN


@dataclass(frozen=True)
class NespressoSensorDescription(SensorEntityDescription):
    value_fn: Any = None


def _reported(d: dict, key: str, default: Any = None) -> Any:
    return d.get("status", {}).get("reported", {}).get(key, default)


SENSOR_TYPES: tuple[NespressoSensorDescription, ...] = (
    NespressoSensorDescription(
        key="machine_status",
        translation_key="machine_status",
        icon="mdi:coffee-maker",
        value_fn=lambda d: NespressoClient.parse_status(_reported(d, "machineStatus", 0)),
    ),
    NespressoSensorDescription(
        key="error_code",
        translation_key="error_code",
        icon="mdi:alert-circle",
        value_fn=lambda d: _reported(d, "errorCode", 0),
    ),
    NespressoSensorDescription(
        key="water_hardness",
        translation_key="water_hardness",
        icon="mdi:water",
        value_fn=lambda d: _reported(d, "waterHardness"),
    ),
    NespressoSensorDescription(
        key="last_coffee",
        translation_key="last_coffee",
        icon="mdi:coffee",
        value_fn=lambda d: NespressoClient.parse_coffee_family(_reported(d, "lastCoffeeFamilyID")),
    ),
    NespressoSensorDescription(
        key="firmware_main",
        translation_key="firmware_main",
        icon="mdi:chip",
        value_fn=lambda d: next(
            (m["FWR"] for m in _reported(d, "machineInfo", []) if m.get("NM") == "fmw-main"), None
        ),
    ),
    NespressoSensorDescription(
        key="firmware_connectivity",
        translation_key="firmware_connectivity",
        icon="mdi:chip",
        value_fn=lambda d: next(
            (m["FWR"] for m in _reported(d, "machineInfo", []) if m.get("NM") == "fmw-connectivity"), None
        ),
    ),
    NespressoSensorDescription(
        key="last_update",
        translation_key="last_update",
        icon="mdi:clock-outline",
        value_fn=lambda d: d.get("presence", {}).get("LastUpdate"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: NespressoCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for machine_id, machine_data in coordinator.data.items():
        machine = machine_data["machine"]
        for description in SENSOR_TYPES:
            entities.append(NespressoSensor(coordinator, machine_id, machine, description))
    async_add_entities(entities)


class NespressoSensor(CoordinatorEntity, SensorEntity):
    entity_description: NespressoSensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, machine_id, machine, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._machine_id = machine_id
        serial = machine.get("serialNumber", machine_id)
        product = machine.get("productId", "").split("/")[-1]
        self._attr_unique_id = f"nespresso_{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=f"Nespresso {product}",
            manufacturer="Nespresso",
            model=product,
            serial_number=serial,
        )

    @property
    def native_value(self) -> Any:
        if self._machine_id not in self.coordinator.data:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data[self._machine_id])
        except (KeyError, TypeError):
            return None
