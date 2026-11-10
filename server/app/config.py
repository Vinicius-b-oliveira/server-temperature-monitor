import os
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent

MQTT_ENABLED = os.getenv("MQTT_ENABLED", "1") != "0"
MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TEAM_CODE = os.getenv("TEAM_CODE", "g2-axr2adzj")
DEVICE_ID = os.getenv("DEVICE_ID", "esp32-rack01")
TOPIC_PREFIX = f"thermomon/{TEAM_CODE}/rack01/"

DB_PATH = Path(os.getenv("DB_PATH", SERVER_DIR / "data" / "monitor.db"))
OFFLINE_AFTER_S = int(os.getenv("OFFLINE_AFTER_S", "15"))

# Limite crítico padrão do firmware, usado enquanto não chega nenhuma leitura
CRITICAL_C = float(os.getenv("CRITICAL_C", "32"))
