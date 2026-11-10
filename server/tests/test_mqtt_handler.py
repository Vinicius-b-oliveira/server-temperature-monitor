import json

from app import database, mqtt_client
from conftest import telemetry_bytes


def kinds(db_path) -> list[str]:
    return [e["kind"] for e in reversed(database.recent_events(db_path, 100))]


def test_valid_reading_is_stored(db_path):
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(temp_c=26.0))
    assert database.latest_reading(db_path)["temp_c"] == 26.0
    assert kinds(db_path) == []


def test_state_change_creates_event(db_path):
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state="normal"))
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state="normal"))
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state="warning"))
    events = database.recent_events(db_path, 10)
    assert [e["kind"] for e in events] == ["state_change"]
    assert json.loads(events[0]["detail"]) == {"from": "normal", "to": "warning"}


def test_fault_creates_sensor_fault_once(db_path):
    for state in ("normal", "fault", "fault", "normal"):
        mqtt_client.handle_message(
            mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state=state, temp_c=None)
        )
    assert kinds(db_path) == ["state_change", "sensor_fault", "state_change"]


def test_first_reading_in_fault_creates_sensor_fault(db_path):
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state="fault"))
    assert kinds(db_path) == ["sensor_fault"]


def test_invalid_telemetry_is_discarded(db_path, caplog):
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, b"{broken")
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(fan_on=1))
    assert database.latest_reading(db_path) is None
    assert "Discarded invalid telemetry" in caplog.text


def test_status_event_only_on_change(db_path):
    for payload in (b"online", b"online", b"offline", b"bogus", b"online"):
        mqtt_client.handle_message(mqtt_client.STATUS_TOPIC, payload)
    assert kinds(db_path) == ["online", "offline", "online"]


def test_other_topics_are_ignored(db_path):
    mqtt_client.handle_message("thermomon/other/rack01/telemetry", telemetry_bytes())
    assert database.latest_reading(db_path) is None
