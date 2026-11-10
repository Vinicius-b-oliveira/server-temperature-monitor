import json

import pytest

from app import config, database


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setattr(config, "DB_PATH", path)
    database.init_db(path)
    return path


def telemetry(**changes) -> dict:
    data = {
        "device": "esp32-rack01", "uptime_s": 1234, "temp_c": 24.31, "dht_temp_c": 24.0,
        "humidity_pct": 41, "lid_open": False, "fan_on": True, "state": "normal", "mode": "auto",
        "warning_c": 27.0, "critical_c": 32.0,
    }
    data.update(changes)
    return data


def telemetry_bytes(**changes) -> bytes:
    return json.dumps(telemetry(**changes)).encode()
