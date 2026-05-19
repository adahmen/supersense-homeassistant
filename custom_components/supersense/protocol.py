"""
SuperSense BLE-Protokoll Dekodierung.

Basiert auf Reverse Engineering der APK de.comworks.supersense v2.11.115.
Relevante Klassen: o9/y.java (Parser), o9/h.java (BLE-Handler), o9/m.java (UUIDs).

Protokoll:
- Der Sensor sendet 8 Bytes als BCD-kodierte Werte (4 × 2 Byte).
- BCD-Dekodierung: Bytes 0x04, 0x27 → String "0427" → int 427
  (NICHT als Hex interpretieren: 0x0427 ≠ 427, sondern 1063)
- Wert 0: Füllstand in ml (Hauptmesswert)
- Wert 1: Temperatur in 1/10 °C (z.B. 235 → 23,5 °C)
- Wert 2: Rohdruckwert des Sensors (interne Einheit)
- Wert 3: Statusinformation / Kalibrierungsstatus
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

INVALID_VALUE = 9999  # Sentinel aus der App (Arrays.fill(iArr, 9999))


@dataclass
class SuperSenseData:
    """Dekodierte Sensordaten."""

    fill_ml: int | None        # Füllstand in ml
    temperature_c: float | None  # Temperatur in °C
    raw_pressure: int | None   # Rohdruckwert
    status: int | None         # Statusbyte

    @property
    def fill_liter(self) -> float | None:
        """Füllstand in Liter."""
        if self.fill_ml is None:
            return None
        return round(self.fill_ml / 1000.0, 2)

    def fill_percent(self, capacity_liter: int) -> float | None:
        """Füllstand in Prozent, bezogen auf Tankkapazität."""
        if self.fill_ml is None or capacity_liter <= 0:
            return None
        return round(min((self.fill_ml / (capacity_liter * 1000)) * 100, 100), 1)

    def is_valid(self) -> bool:
        """Prüft ob die Daten plausibel sind."""
        return self.fill_ml is not None and self.fill_ml != INVALID_VALUE


def _decode_bcd_pair(hi: int, lo: int) -> int | None:
    """
    Dekodiert zwei Bytes als BCD-Wert.

    Direkt aus o9/y.java:
        Integer.parseInt(String.format("%02x%02x", byte0, byte1), 10)

    Beispiel: hi=0x04, lo=0x27 → "0427" → 427
    Gibt None zurück wenn der Wert 9999 (Sentinel) ist.
    """
    try:
        value = int(f"{hi:02x}{lo:02x}", 10)
    except ValueError:
        _LOGGER.warning("BCD-Dekodierung fehlgeschlagen für Bytes: 0x%02x 0x%02x", hi, lo)
        return None

    if value == INVALID_VALUE:
        return None

    return value


def decode_payload(data: bytes | bytearray) -> SuperSenseData | None:
    """
    Dekodiert den 8-Byte-Payload des SuperSense Sensors.

    Gibt None zurück wenn die Länge falsch ist.
    """
    if len(data) != 8:
        _LOGGER.debug("Ungültige Payload-Länge: %d (erwartet 8)", len(data))
        return None

    raw = [_decode_bcd_pair(data[i], data[i + 1]) for i in range(0, 8, 2)]

    _LOGGER.debug(
        "SuperSense Rohwerte: %s → dekodiert: %s",
        data.hex(),
        raw,
    )

    fill_ml = raw[0]
    temp_raw = raw[1]
    pressure_raw = raw[2]
    status = raw[3]

    # Temperatur: Rohwert in 1/10 °C, z.B. 235 → 23.5 °C
    temperature_c: float | None = None
    if temp_raw is not None and temp_raw != 0:
        temperature_c = round(temp_raw / 10.0, 1)

    return SuperSenseData(
        fill_ml=fill_ml,
        temperature_c=temperature_c,
        raw_pressure=pressure_raw,
        status=status,
    )
