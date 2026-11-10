import json
import logging
import sqlite3
import uuid

import paho.mqtt.client as mqtt

from app import config, database, validation

log = logging.getLogger(__name__)

TELEMETRY_TOPIC = config.TOPIC_PREFIX + "telemetry"
STATUS_TOPIC = config.TOPIC_PREFIX + "status"

_client: mqtt.Client | None = None


def handle_message(topic: str, payload: bytes) -> None:
    if topic == TELEMETRY_TOPIC:
        _handle_telemetry(payload)
    elif topic == STATUS_TOPIC:
        _handle_status(payload)


def _handle_telemetry(payload: bytes) -> None:
    reading = validation.validate_telemetry(payload)
    if reading is None:
        log.warning("Discarded invalid telemetry: %r", payload[:80])
        return

    previous = database.latest_reading(config.DB_PATH)
    database.insert_reading(config.DB_PATH, reading)

    old_state = previous["state"] if previous else None
    new_state = reading["state"]
    if old_state is not None and old_state != new_state:
        detail = json.dumps({"from": old_state, "to": new_state})
        database.insert_event(config.DB_PATH, reading["device"], "state_change", detail)
    if new_state == "fault" and old_state != "fault":
        database.insert_event(config.DB_PATH, reading["device"], "sensor_fault")


def _handle_status(payload: bytes) -> None:
    status = validation.validate_status(payload)
    if status is None:
        log.warning("Discarded invalid status: %r", payload[:80])
        return
    # O status é retido no broker e chega de novo a cada reconexão
    if database.last_status(config.DB_PATH) != status:
        database.insert_event(config.DB_PATH, config.DEVICE_ID, status)


def _on_connect(client, userdata, flags, reason_code, properties) -> None:
    if reason_code.is_failure:
        log.warning("MQTT connection refused: %s", reason_code)
        return
    log.info("MQTT connected to %s", config.MQTT_HOST)
    client.subscribe([(TELEMETRY_TOPIC, 0), (STATUS_TOPIC, 0)])


def _on_disconnect(client, userdata, flags, reason_code, properties) -> None:
    log.warning("MQTT disconnected: %s", reason_code)


# Uma exceção aqui derrubaria a thread de rede do paho e o servidor pararia de receber
def _on_message(client, userdata, message) -> None:
    try:
        handle_message(message.topic, message.payload)
    except sqlite3.Error as err:
        log.error("Database error: %s", err)


def start() -> None:
    global _client
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"thermomon-server-{uuid.uuid4().hex[:8]}",
    )
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(config.MQTT_HOST, config.MQTT_PORT, keepalive=30)
    client.loop_start()
    _client = client


def stop() -> None:
    global _client
    if _client is None:
        return
    _client.disconnect()
    _client.loop_stop()
    _client = None


def publish_command(name: str, payload: str) -> bool:
    if _client is None:
        return False
    info = _client.publish(config.TOPIC_PREFIX + "cmd/" + name, payload, qos=0, retain=False)
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        log.warning("Command %s not sent: %s", name, mqtt.error_string(info.rc))
        return False
    detail = json.dumps({"name": name, "payload": payload})
    database.insert_event(config.DB_PATH, config.DEVICE_ID, "command", detail)
    return True
