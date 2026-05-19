# SuperSense Home Assistant Integration

Custom Integration für den **Comworks SuperSense** Füllstandssensor in Home Assistant.

Verbindet sich **direkt per Bluetooth** mit dem Sensor – kein ESP32, kein Zigbee-Coordinator nötig.

## Unterstützte Geräte

- SuperSense Pro (Füllstandssensor für Wasser, Abwasser, Gas)
- SuperSense Solid
- SuperSense Laser *(ungetestet, gleiche BLE-Architektur)*

## Voraussetzungen

- Home Assistant auf Raspberry Pi 4 (Bluetooth 5.0 onboard)
- SuperSense Sensor mit Bluetooth-Modul
- Home Assistant OS oder Supervised

## Installation via HACS

1. HACS öffnen → Integrationen → `+` → **Benutzerdefiniertes Repository hinzufügen**
2. URL: `https://github.com/adahmen/supersense-homeassistant`
3. Kategorie: **Integration**
4. SuperSense suchen und installieren
5. Home Assistant neu starten

## Manuelle Installation

```bash
# Im Home Assistant Konfigurationsordner:
cd /config/custom_components/
git clone https://github.com/adahmen/supersense-homeassistant temp
cp -r temp/custom_components/supersense .
rm -rf temp
```

Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Integrationen → Integration hinzufügen**
2. Nach **SuperSense** suchen
3. Sensor wird automatisch erkannt (wenn eingeschaltet und in Reichweite)
4. Name und Tankkapazität eingeben

## Bereitgestellte Sensoren

| Sensor | Einheit | Beschreibung |
|--------|---------|--------------|
| Füllstand | Liter | Aktueller Füllstand |
| Füllstand % | % | Füllstand relativ zur konfigurierten Kapazität |
| Füllstand Rohwert | ml | Rohwert in Milliliter (für Debugging) |
| Temperatur | °C | Sensortemperatur |

## Technischer Hintergrund

Das BLE-Protokoll wurde durch Reverse Engineering der Android-App
`de.comworks.supersense` v2.11.115 ermittelt.

### GATT-Struktur

| UUID | Funktion |
|------|----------|
| `a0eeb190-6b2a-45fb-966e-d8e49323691f` | Haupt-Service |
| `0bd4c5d4-62e3-4946-82ea-d7643834d368` | Messwert-Notifications |
| `8215dd0f-cc20-4d2a-8b64-73907ec4bd16` | Befehle (Write) |

### Datenformat

Der Sensor sendet 8 Bytes als 4 × BCD-kodierte 16-bit-Werte:

```
Byte 0+1: Füllstand in ml (BCD)
Byte 2+3: Temperatur in 1/10 °C (BCD)
Byte 4+5: Rohdruckwert (BCD)
Byte 6+7: Status/Kalibrierung (BCD)
```

**BCD-Dekodierung:** `bytes [0x04, 0x27]` → String `"0427"` → int `427` ml

## Fehlerbehebung

**Sensor wird nicht erkannt:**
- Bluetooth in HA aktiviert? → Einstellungen → System → Hardware
- Sensor eingeschaltet und < 10 m entfernt?
- `bluetoothctl scan on` im Terminal prüfen ob MAC sichtbar ist

**Verbindung bricht ständig ab:**
- SuperSense Bluetooth-Reichweite beträgt ca. 10 m
- Metallgehäuse oder Wassertanks können das Signal dämpfen
- Bluetooth-Proxy (ESP32) als Reichweitenverstärker möglich

**Falsche Füllstand-Werte:**
- Tankkapazität in der Integration korrekt eingestellt?
- Sensor neu kalibrieren (Knopf am Sensor, laut SuperSense Anleitung)

## Lizenz

MIT License – siehe [LICENSE](LICENSE)
