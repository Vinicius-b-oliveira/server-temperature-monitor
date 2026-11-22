import pytest

from app import config, mqtt_client, telegram
from conftest import telemetry, telemetry_bytes


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_TOKEN", "test-token")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "123")


def test_disabled_without_token(db_path, telegram_messages):
    telegram.notify_state_change("normal", telemetry(state="critical"))
    assert telegram_messages == []


@pytest.mark.parametrize("state", ["warning", "critical", "fault"])
def test_alert_states_send_message(enabled, telegram_messages, state):
    telegram.notify_state_change("normal", telemetry(state=state))
    assert len(telegram_messages) == 1


def test_normal_and_same_state_send_nothing(enabled, telegram_messages):
    telegram.notify_state_change("warning", telemetry(state="normal"))
    telegram.notify_state_change("critical", telemetry(state="critical"))
    assert telegram_messages == []


def test_same_alert_waits_min_interval(enabled, telegram_messages, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(telegram, "_now", lambda: clock[0])
    telegram.notify_state_change("normal", telemetry(state="warning"))
    clock[0] += telegram.MIN_INTERVAL_S - 1
    telegram.notify_state_change("normal", telemetry(state="warning"))
    telegram.notify_state_change("warning", telemetry(state="critical"))
    clock[0] += 1
    telegram.notify_state_change("normal", telemetry(state="warning"))
    assert len(telegram_messages) == 3


def test_message_text():
    reading = telemetry(state="critical", temp_c=33.06, critical_c=32.0)
    assert telegram.format_message(reading) == "esp32-rack01: estado crítico, 33,1 °C (limite de 32,0 °C)."
    fault = telegram.format_message(telemetry(state="fault", temp_c=None))
    assert fault.startswith("esp32-rack01: falha no sensor")


def test_telemetry_state_change_triggers_alert(db_path, enabled, telegram_messages):
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state="normal"))
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state="warning", temp_c=27.4))
    mqtt_client.handle_message(mqtt_client.TELEMETRY_TOPIC, telemetry_bytes(state="warning", temp_c=27.6))
    assert telegram_messages == ["esp32-rack01: atenção, 27,4 °C (limite de 27,0 °C)."]
