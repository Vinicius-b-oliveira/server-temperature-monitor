import json

import pytest

from app.validation import (
    MAX_PAYLOAD_BYTES, limits_are_valid, validate_status, validate_telemetry,
)
from conftest import telemetry, telemetry_bytes


def test_valid_telemetry_is_accepted():
    assert validate_telemetry(telemetry_bytes()) == telemetry()


def test_integer_limits_are_accepted():
    assert validate_telemetry(telemetry_bytes(warning_c=28, critical_c=31)) is not None


def test_null_sensor_values_are_accepted():
    raw = telemetry_bytes(temp_c=None, dht_temp_c=None, humidity_pct=None, state="fault")
    assert validate_telemetry(raw) is not None


# Caso 17 do plano de testes
@pytest.mark.parametrize("raw", [b"{not json", b"", b"[1, 2]", b'"text"', b"\xff\xfe"])
def test_malformed_payload_is_rejected(raw):
    assert validate_telemetry(raw) is None


@pytest.mark.parametrize("changes", [
    {"uptime_s": "1234"},
    {"uptime_s": -1},
    {"uptime_s": 12.5},
    {"temp_c": "24"},
    {"temp_c": 200},
    {"temp_c": float("nan")},
    {"humidity_pct": 41.5},
    {"humidity_pct": 101},
    {"lid_open": 0},
    {"fan_on": 1},
    {"fan_on": "true"},
    {"state": "hot"},
    {"state": ["normal"]},
    {"mode": "remote"},
    {"warning_c": 15.0},
    {"critical_c": 55.0},
    {"warning_c": 30.0, "critical_c": 32.0},
    {"warning_c": True},
    {"critical_c": "32"},
    {"critical_c": None},
])
def test_wrong_type_or_range_is_rejected(changes):
    assert validate_telemetry(telemetry_bytes(**changes)) is None


def test_missing_or_extra_key_is_rejected():
    data = telemetry()
    del data["mode"]
    assert validate_telemetry(json.dumps(data).encode()) is None
    assert validate_telemetry(telemetry_bytes(extra=1)) is None


# Caso 18: o device com HTML não é o configurado, então nem chega ao banco
def test_html_in_device_is_rejected():
    raw = telemetry_bytes(device="<img src=x onerror=alert(1)>")
    assert validate_telemetry(raw) is None


def test_unknown_device_is_rejected():
    assert validate_telemetry(telemetry_bytes(device="esp32-other")) is None


def test_oversized_payload_is_rejected():
    padded = telemetry_bytes()[:-1] + b" " * MAX_PAYLOAD_BYTES + b"}"
    assert validate_telemetry(padded[:MAX_PAYLOAD_BYTES - 1] + b"}") is not None
    assert validate_telemetry(padded) is None


def test_status():
    assert validate_status(b"online") == "online"
    assert validate_status(b"offline") == "offline"
    assert validate_status(b"ONLINE") is None
    assert validate_status(b"\xff") is None


@pytest.mark.parametrize("warning, critical, expected", [
    (27, 32, True),
    (20, 23, True),
    (47, 50, True),
    (27, 29, False),
    (19, 32, False),
    (27, 51, False),
    (5, 90, False),
])
def test_limits(warning, critical, expected):
    assert limits_are_valid(warning, critical) is expected
