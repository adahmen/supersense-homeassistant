"""
SuperSense DataUpdateCoordinator.

Verwaltet die BLE-Verbindung, Reconnect-Logik und
verteilt Sensor-Updates an alle Entitäten.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Callable

from bleak import BleakClient, BleakError
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CHAR_NOTIFY_UUID,
    CHAR_WRITE_UUID,
    CONNECT_TIMEOUT,
    DOMAIN,
    EXPECTED_PAYLOAD_LENGTH,
    INIT_PACKET,
    NOTIFY_TIMEOUT,
    RECONNECT_DELAY,
)
from .protocol import SuperSenseData, decode_payload

_LOGGER = logging.getLogger(__name__)


class SuperSenseCoordinator(DataUpdateCoordinator[SuperSenseData]):
    """
    Koordiniert die BLE-Verbindung zum SuperSense Sensor.

    Verwendet HA's Bluetooth-Integration (bleak unter BlueZ)
    direkt auf dem Raspberry Pi – kein ESP32 erforderlich.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        mac: str,
        name: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"SuperSense {name}",
        )
        self.mac = mac
        self.sensor_name = name
        self._client: BleakClient | None = None
        self._connected = False
        self._last_data: SuperSenseData | None = None
        self._last_data_time: datetime | None = None
        self._reconnect_task: asyncio.Task | None = None
        self._notify_watchdog_task: asyncio.Task | None = None
        self._listeners: list[Callable] = []

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        """Startet die BLE-Verbindung."""
        _LOGGER.info("Starte SuperSense Verbindung zu %s", self.mac)
        await self._connect()

    async def async_stop(self) -> None:
        """Trennt die BLE-Verbindung sauber."""
        _LOGGER.info("Stoppe SuperSense Verbindung zu %s", self.mac)
        self._cancel_tasks()
        await self._disconnect()

    @property
    def connected(self) -> bool:
        """True wenn BLE-Verbindung aktiv ist."""
        return self._connected

    @property
    def last_data(self) -> SuperSenseData | None:
        """Zuletzt empfangene Sensordaten."""
        return self._last_data

    # ------------------------------------------------------------------
    # Verbindungsmanagement
    # ------------------------------------------------------------------

    async def _connect(self) -> None:
        """Baut BLE-Verbindung auf und aktiviert Notifications."""
        try:
            _LOGGER.debug("Verbinde mit %s ...", self.mac)

            # Prüfen ob Gerät via HA-Bluetooth-Scanner sichtbar ist
            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.mac, connectable=True
            )
            if ble_device is None:
                _LOGGER.warning(
                    "SuperSense %s nicht gefunden. Stelle sicher dass der Sensor "
                    "eingeschaltet und in Reichweite ist.",
                    self.mac,
                )
                self._schedule_reconnect()
                return

            self._client = BleakClient(
                ble_device,
                timeout=CONNECT_TIMEOUT,
                disconnected_callback=self._on_disconnected,
            )

            await self._client.connect()
            self._connected = True
            _LOGGER.info("SuperSense %s verbunden.", self.mac)

            # Initialisierungspaket senden (wie in der App: o9/b.java)
            await self._client.write_gatt_char(CHAR_WRITE_UUID, INIT_PACKET)
            _LOGGER.debug("Init-Paket gesendet: %s", INIT_PACKET.hex())

            # Notifications für Messwerte aktivieren
            await self._client.start_notify(CHAR_NOTIFY_UUID, self._on_notify)
            _LOGGER.debug("Notifications aktiviert auf %s", CHAR_NOTIFY_UUID)

            # Watchdog starten der bei Datenstillstand neu verbindet
            self._start_notify_watchdog()

        except BleakError as err:
            _LOGGER.error("BLE-Verbindungsfehler zu %s: %s", self.mac, err)
            self._connected = False
            self._schedule_reconnect()
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout beim Verbinden mit %s", self.mac)
            self._connected = False
            self._schedule_reconnect()

    async def _disconnect(self) -> None:
        """Trennt BLE-Verbindung."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(CHAR_NOTIFY_UUID)
                await self._client.disconnect()
            except BleakError as err:
                _LOGGER.debug("Fehler beim Trennen: %s", err)
        self._client = None
        self._connected = False

    @callback
    def _on_disconnected(self, client: BleakClient) -> None:
        """Callback wenn BLE-Verbindung unerwartet getrennt wird."""
        _LOGGER.warning("SuperSense %s Verbindung getrennt.", self.mac)
        self._connected = False
        self._cancel_tasks()
        self._schedule_reconnect()

    def _schedule_reconnect(self) -> None:
        """Plant Wiederverbindung nach Wartezeit."""
        if self._reconnect_task and not self._reconnect_task.done():
            return
        self._reconnect_task = self.hass.async_create_task(
            self._reconnect_after_delay()
        )

    async def _reconnect_after_delay(self) -> None:
        """Wartet und verbindet neu."""
        _LOGGER.debug(
            "Wiederverbindung zu %s in %.0f Sekunden ...",
            self.mac,
            RECONNECT_DELAY,
        )
        await asyncio.sleep(RECONNECT_DELAY)
        await self._connect()

    # ------------------------------------------------------------------
    # Notify-Empfang
    # ------------------------------------------------------------------

    @callback
    def _on_notify(self, sender: int, data: bytearray) -> None:
        """Wird aufgerufen wenn der Sensor neue Messdaten sendet."""
        _LOGGER.debug(
            "Notify von %s: %s (%d Bytes)",
            self.mac,
            data.hex(),
            len(data),
        )

        if len(data) != EXPECTED_PAYLOAD_LENGTH:
            _LOGGER.warning(
                "Unerwartete Payload-Länge: %d Bytes (erwartet %d). "
                "Rohdaten: %s",
                len(data),
                EXPECTED_PAYLOAD_LENGTH,
                data.hex(),
            )
            return

        sensor_data = decode_payload(data)
        if sensor_data is None:
            return

        self._last_data = sensor_data
        self._last_data_time = datetime.now()

        # Alle registrierten Sensoren über neue Daten informieren
        self.async_set_updated_data(sensor_data)

    # ------------------------------------------------------------------
    # Watchdog
    # ------------------------------------------------------------------

    def _start_notify_watchdog(self) -> None:
        """Startet Watchdog-Task der bei Datenstillstand neu verbindet."""
        if self._notify_watchdog_task and not self._notify_watchdog_task.done():
            self._notify_watchdog_task.cancel()
        self._notify_watchdog_task = self.hass.async_create_task(
            self._notify_watchdog()
        )

    async def _notify_watchdog(self) -> None:
        """Prüft periodisch ob Daten empfangen werden."""
        await asyncio.sleep(NOTIFY_TIMEOUT)
        if not self._connected:
            return
        last = self._last_data_time
        if last is None or (datetime.now() - last).total_seconds() > NOTIFY_TIMEOUT:
            _LOGGER.warning(
                "SuperSense %s sendet seit %.0f Sekunden keine Daten. "
                "Verbindung wird neu aufgebaut.",
                self.mac,
                NOTIFY_TIMEOUT,
            )
            await self._disconnect()
            self._schedule_reconnect()

    # ------------------------------------------------------------------
    # Internes
    # ------------------------------------------------------------------

    def _cancel_tasks(self) -> None:
        """Bricht alle laufenden Tasks ab."""
        for task in (self._reconnect_task, self._notify_watchdog_task):
            if task and not task.done():
                task.cancel()

    async def _async_update_data(self) -> SuperSenseData:
        """Wird von DataUpdateCoordinator aufgerufen (hier nicht genutzt, push-basiert)."""
        if self._last_data is None:
            raise UpdateFailed("Noch keine Daten vom SuperSense Sensor empfangen.")
        return self._last_data
