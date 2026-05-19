"""
Config Flow für SuperSense Integration.

Ermöglicht das Hinzufügen des Sensors über die HA-Oberfläche:
Einstellungen → Integrationen → SuperSense hinzufügen
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MAC,
    CONF_TANK_CAPACITY,
    DEFAULT_NAME,
    DEFAULT_TANK_CAPACITY,
    DOMAIN,
    SERVICE_UUID,
)

_LOGGER = logging.getLogger(__name__)


class SuperSenseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow für SuperSense Füllstandssensor."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_devices: dict[str, str] = {}  # mac → name
        self._selected_mac: str | None = None

    # ------------------------------------------------------------------
    # Schritt 1: Automatische Erkennung via Bluetooth-Scan
    # ------------------------------------------------------------------

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """
        Wird aufgerufen wenn HA automatisch einen SuperSense Sensor erkennt
        (via Service UUID im manifest.json).
        """
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._selected_mac = discovery_info.address
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_confirm()

    # ------------------------------------------------------------------
    # Schritt 2: Manuelle Eingabe (wenn Sensor nicht automatisch erkannt)
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schritt: Benutzer wählt Sensor aus gescannten Geräten."""

        # Alle sichtbaren SuperSense-Geräte sammeln
        self._discovered_devices = {}
        for info in bluetooth.async_discovered_service_info(self.hass):
            if SERVICE_UUID.lower() in [s.lower() for s in info.service_uuids]:
                self._discovered_devices[info.address] = (
                    info.name or info.address
                )

        if user_input is not None:
            self._selected_mac = user_input[CONF_MAC]
            await self.async_set_unique_id(self._selected_mac)
            self._abort_if_unique_id_configured()
            return await self.async_step_setup()

        # Wenn Geräte gefunden → Auswahlliste, sonst manuelles Eingabefeld
        if self._discovered_devices:
            schema = vol.Schema(
                {
                    vol.Required(CONF_MAC): vol.In(
                        {
                            mac: f"{name} ({mac})"
                            for mac, name in self._discovered_devices.items()
                        }
                    )
                }
            )
            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                description_placeholders={
                    "count": str(len(self._discovered_devices))
                },
            )

        # Kein Gerät gefunden → manuelle MAC-Eingabe
        schema = vol.Schema(
            {
                vol.Required(CONF_MAC): str,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors={"base": "no_devices_found"} if user_input is not None else {},
        )

    # ------------------------------------------------------------------
    # Schritt 3: Name + Tankkapazität konfigurieren
    # ------------------------------------------------------------------

    async def async_step_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schritt: Name und Tankkapazität eingeben."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_MAC: self._selected_mac,
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_TANK_CAPACITY: user_input[CONF_TANK_CAPACITY],
                },
            )

        # Vorgeschlagener Name aus Bluetooth-Scan
        suggested_name = DEFAULT_NAME
        if self._selected_mac and self._selected_mac in self._discovered_devices:
            suggested_name = self._discovered_devices[self._selected_mac]

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=suggested_name): str,
                vol.Required(
                    CONF_TANK_CAPACITY, default=DEFAULT_TANK_CAPACITY
                ): vol.All(int, vol.Range(min=1, max=10000)),
            }
        )
        return self.async_show_form(step_id="setup", data_schema=schema)

    # ------------------------------------------------------------------
    # Schritt: Bestätigung bei automatischer Erkennung
    # ------------------------------------------------------------------

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bestätigungsschritt nach automatischer Erkennung."""
        if user_input is not None:
            return await self.async_step_setup()

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={"mac": self._selected_mac},
        )
