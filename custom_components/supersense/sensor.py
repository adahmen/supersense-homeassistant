"""
SuperSense Sensor-Entitäten.

Erstellt folgende Sensoren pro Gerät:
- Füllstand (Liter)
- Füllstand (Prozent)
- Füllstand Rohwert (ml)
- Temperatur (°C)
- Verbindungsstatus
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_MAC,
    CONF_NAME,
    CONF_TANK_CAPACITY,
    DOMAIN,
    SENSOR_FILL_LEVEL_LITER,
    SENSOR_FILL_LEVEL_PERCENT,
    SENSOR_FILL_LEVEL_RAW,
    SENSOR_TEMPERATURE,
)
from .coordinator import SuperSenseCoordinator
from .protocol import SuperSenseData

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SuperSenseSensorDescription(SensorEntityDescription):
    """Beschreibung einer SuperSense Sensor-Entität."""

    value_fn: Callable[[SuperSenseData, int], float | int | None]


def _make_descriptions(tank_capacity: int) -> list[SuperSenseSensorDescription]:
    """Erstellt Sensor-Beschreibungen mit der konfigurierten Tankkapazität."""
    return [
        SuperSenseSensorDescription(
            key=SENSOR_FILL_LEVEL_LITER,
            name="Füllstand",
            native_unit_of_measurement=UnitOfVolume.LITERS,
            device_class=SensorDeviceClass.VOLUME_STORAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:water",
            value_fn=lambda d, _: d.fill_liter,
        ),
        SuperSenseSensorDescription(
            key=SENSOR_FILL_LEVEL_PERCENT,
            name="Füllstand %",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:water-percent",
            value_fn=lambda d, cap: d.fill_percent(cap),
        ),
        SuperSenseSensorDescription(
            key=SENSOR_FILL_LEVEL_RAW,
            name="Füllstand Rohwert",
            native_unit_of_measurement="ml",
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:water-outline",
            entity_registry_enabled_default=False,  # Standardmäßig ausgeblendet
            value_fn=lambda d, _: d.fill_ml,
        ),
        SuperSenseSensorDescription(
            key=SENSOR_TEMPERATURE,
            name="Temperatur",
            native_unit_of_measurement=UnitOfTemperature.CELSIUS,
            device_class=SensorDeviceClass.TEMPERATURE,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:thermometer",
            value_fn=lambda d, _: d.temperature_c,
        ),
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richtet Sensor-Entitäten ein."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: SuperSenseCoordinator = data["coordinator"]
    tank_capacity: int = data["tank_capacity"]

    mac = entry.data[CONF_MAC]
    name = entry.data[CONF_NAME]

    descriptions = _make_descriptions(tank_capacity)

    entities = [
        SuperSenseSensorEntity(
            coordinator=coordinator,
            description=desc,
            mac=mac,
            device_name=name,
            tank_capacity=tank_capacity,
        )
        for desc in descriptions
    ]

    async_add_entities(entities)


class SuperSenseSensorEntity(CoordinatorEntity[SuperSenseCoordinator], SensorEntity):
    """Eine einzelne Sensor-Entität des SuperSense."""

    entity_description: SuperSenseSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SuperSenseCoordinator,
        description: SuperSenseSensorDescription,
        mac: str,
        device_name: str,
        tank_capacity: int,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._mac = mac
        self._device_name = device_name
        self._tank_capacity = tank_capacity

        # Eindeutige ID: MAC + Sensor-Key
        self._attr_unique_id = f"{mac}_{description.key}"

        # Geräteinformation (fasst alle Sensoren eines Geräts zusammen)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=device_name,
            manufacturer="Comworks",
            model="SuperSense Pro",
            sw_version="2.11.115",
        )

    @property
    def native_value(self) -> float | int | None:
        """Aktueller Messwert."""
        if self.coordinator.last_data is None:
            return None
        return self.entity_description.value_fn(
            self.coordinator.last_data, self._tank_capacity
        )

    @property
    def available(self) -> bool:
        """Sensor ist verfügbar wenn BLE-Verbindung aktiv und Daten vorhanden."""
        return self.coordinator.connected and self.coordinator.last_data is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Wird aufgerufen wenn neue Daten vom Coordinator vorliegen."""
        self.async_write_ha_state()
