import json
import threading
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import config, database, mqtt_client
from app.main import app
from conftest import telemetry, telemetry_bytes


class FakeMqttClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos, retain):
        self.published.append((topic, payload, qos, retain))
        return SimpleNamespace(rc=0)


@pytest.fixture
def client(db_path, monkeypatch):
    monkeypatch.setattr(config, "MQTT_ENABLED", False)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fake_mqtt(monkeypatch):
    fake = FakeMqttClient()
    monkeypatch.setattr(mqtt_client, "_client", fake)
    return fake


def test_latest_empty(client):
    assert client.get("/api/latest").json() == {"online": False, "reading": None}


def test_latest_online_with_fresh_reading(client, db_path):
    database.insert_reading(db_path, telemetry(temp_c=25.0))
    body = client.get("/api/latest").json()
    assert body["online"] is True
    assert body["reading"]["temp_c"] == 25.0


def test_latest_offline_when_old_or_status_offline(client, db_path):
    database.insert_reading(db_path, telemetry(), received_at="2020-01-01T00:00:00+00:00")
    assert client.get("/api/latest").json()["online"] is False
    database.insert_reading(db_path, telemetry())
    database.insert_event(db_path, "esp32-rack01", "offline")
    assert client.get("/api/latest").json()["online"] is False


def test_readings_and_bounds(client, db_path):
    database.insert_reading(db_path, telemetry(temp_c=24.0))
    assert [r["temp_c"] for r in client.get("/api/readings?minutes=60").json()] == [24.0]
    assert client.get("/api/readings?minutes=0").status_code == 422
    assert client.get("/api/readings?minutes=1441").status_code == 422


def test_events_and_bounds(client, db_path):
    database.insert_event(db_path, "esp32-rack01", "online")
    assert client.get("/api/events").json()[0]["kind"] == "online"
    assert client.get("/api/events?limit=501").status_code == 422


def test_indicators_without_data(client):
    body = client.get("/api/indicators").json()
    assert body == {"rate_c_per_min": None, "minutes_to_critical": None, "critical_c": 32.0}


def test_indicators_use_critical_from_latest_reading(client, db_path):
    database.insert_reading(db_path, telemetry(critical_c=35.0))
    assert client.get("/api/indicators").json()["critical_c"] == 35.0


def test_commands_publish_and_record_event(client, fake_mqtt, db_path):
    assert client.post("/api/commands/mode", json={"mode": "manual"}).status_code == 200
    assert client.post("/api/commands/fan", json={"fan": "off"}).status_code == 200
    assert client.post("/api/commands/limits", json={"warning": 28, "critical": 33}).status_code == 200
    assert client.post("/api/commands/silence").status_code == 200

    prefix = config.TOPIC_PREFIX
    assert fake_mqtt.published == [
        (prefix + "cmd/mode", "manual", 0, False),
        (prefix + "cmd/fan", "off", 0, False),
        (prefix + "cmd/limits", '{"warning": 28, "critical": 33}', 0, False),
        (prefix + "cmd/silence", "1", 0, False),
    ]
    events = database.recent_events(db_path, 10)
    assert [e["kind"] for e in events] == ["command"] * 4
    assert json.loads(events[0]["detail"]) == {"name": "silence", "payload": "1"}


@pytest.mark.parametrize("path, body, status", [
    ("/api/commands/mode", {"mode": "turbo"}, 422),
    ("/api/commands/fan", {"fan": "<b>on</b>"}, 422),
    ("/api/commands/limits", {"warning": 5, "critical": 90}, 400),
    ("/api/commands/limits", {"warning": 30, "critical": 31}, 400),
    ("/api/commands/limits", {"warning": "x", "critical": 32}, 422),
])
def test_invalid_commands_are_rejected(client, fake_mqtt, path, body, status):
    assert client.post(path, json=body).status_code == status
    assert fake_mqtt.published == []


def test_command_without_broker_returns_503(client, db_path):
    assert client.post("/api/commands/silence").status_code == 503
    assert database.recent_events(db_path, 10) == []


# Caso 13: o MQTT grava enquanto o painel consulta
def test_concurrent_writes_and_reads(client, db_path):
    total = 200
    errors = []

    def writer():
        for i in range(total):
            payload = telemetry_bytes(uptime_s=i, state="warning" if i % 10 == 0 else "normal")
            try:
                mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, payload)
            except Exception as err:
                errors.append(err)

    thread = threading.Thread(target=writer)
    thread.start()
    while thread.is_alive():
        assert client.get("/api/latest").status_code == 200
        assert client.get("/api/readings?minutes=5").status_code == 200
        assert client.get("/api/events").status_code == 200
    thread.join()

    assert errors == []
    assert len(client.get("/api/readings?minutes=5").json()) == total
