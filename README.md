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

