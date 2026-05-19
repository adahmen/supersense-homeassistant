"""Konstanten für die SuperSense Integration."""

DOMAIN = "supersense"

# GATT UUIDs – aus APK-Analyse (o9/m.java)
SERVICE_UUID = "a0eeb190-6b2a-45fb-966e-d8e49323691f"
CHAR_NOTIFY_UUID = "0bd4c5d4-62e3-4946-82ea-d7643834d368"   # Füllstand + Temp (notify)
CHAR_WRITE_UUID = "8215dd0f-cc20-4d2a-8b64-73907ec4bd16"    # Befehle senden
CHAR_TEMP_UUID = "8d81b2f7-e56f-44bf-94ee-94083f5ea6d7"     # Temperatur (optional)

# Initialisierungspaket (o9/m.java: f10655e = new byte[]{14, 1, 2, 3, 4, 5, 6})
INIT_PACKET = bytes([0x0E, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06])

# Payload-Länge die der Sensor sendet
EXPECTED_PAYLOAD_LENGTH = 8

# Verbindungs-Timeouts
CONNECT_TIMEOUT = 15.0      # Sekunden
RECONNECT_DELAY = 10.0      # Sekunden bei Verbindungsverlust
NOTIFY_TIMEOUT = 70.0       # Sekunden ohne Daten → Neuverbindung

# Config-Entry Keys
CONF_MAC = "mac"
CONF_NAME = "name"
CONF_TANK_CAPACITY = "tank_capacity"

# Default-Werte
DEFAULT_NAME = "SuperSense Wassertank"
DEFAULT_TANK_CAPACITY = 100  # Liter

# Sensor-Entitäts-Keys
SENSOR_FILL_LEVEL_LITER = "fill_level_liter"
SENSOR_FILL_LEVEL_PERCENT = "fill_level_percent"
SENSOR_FILL_LEVEL_RAW = "fill_level_raw"
SENSOR_TEMPERATURE = "temperature"
SENSOR_SIGNAL_STRENGTH = "signal_strength"
