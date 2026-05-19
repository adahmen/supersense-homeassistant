"""
SuperSense Füllstandssensor – Home Assistant Integration.

Unterstützt:
- Direkte BLE-Verbindung via Raspberry Pi Bluetooth (kein ESP32 nötig)
- Automatische Geräteerkennung
- Automatische Wiederverbindung bei Verbindungsverlust
- Füllstand in Liter, Prozent und Rohwert
- Temperatur
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_MAC, CONF_NAME, CONF_TANK_CAPACITY, DOMAIN
from .coordinator import SuperSenseCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Richtet die SuperSense Integration ein."""
    mac = entry.data[CONF_MAC]
    name = entry.data[CONF_NAME]

    coordinator = SuperSenseCoordinator(hass, mac, name)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "tank_capacity": entry.data.get(CONF_TANK_CAPACITY, 100),
    }

    # BLE-Verbindung starten
    await coordinator.async_start()

    # Sensor-Plattform laden
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Cleanup bei Entfernung der Integration
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Räumt auf wenn Integration entfernt wird."""
    coordinator: SuperSenseCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]
    await coordinator.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Wird aufgerufen wenn Optionen geändert werden."""
    await hass.config_entries.async_reload(entry.entry_id)
