"""Binary sensor platform for Nespresso integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NespressoCoordinator
from .const import DOMAIN


@dataclass(frozen=True)
class NespressoBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Any = None


def _reported(d: dict, key: str, default: Any = None) -> Any:
    return d.get("status", {}).get("reported", {}).get(key, default)


BINARY_SENSOR_TYPES: tuple[NespressoBinarySensorDescription, ...] = (
    NespressoBinarySensorDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: bool(d.get("presence", {}).get("Connected", False)),
    ),
    NespressoBinarySensorDescription(
        key="descaling_alert",
        translation_key="descaling_alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:water-alert",
        value_fn=lambda d: bool(_reported(d, "descalingAlert", False)),
    ),
    NespressoBinarySensorDescription(
        key="error",
        translation_key="error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: int(_reported(d, "errorCode", 0)) != 0,
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
        for description in BINARY_SENSOR_TYPES:
            entities.append(NespressoBinarySensor(coordinator, machine_id, machine, description))
    async_add_entities(entities)


class NespressoBinarySensor(CoordinatorEntity, BinarySensorEntity):
    entity_description: NespressoBinarySensorDescription
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
    def is_on(self) -> bool | None:
        if self._machine_id not in self.coordinator.data:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data[self._machine_id])
        except (KeyError, TypeError):
            return None
