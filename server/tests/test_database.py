import json

from app import database
from conftest import telemetry


def test_init_db_creates_tables_and_wal(db_path):
    with database._connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert {"readings", "events"} <= tables
    assert mode == "wal"


def test_init_db_creates_missing_folder(tmp_path):
    path = tmp_path / "data" / "monitor.db"
    database.init_db(path)
    assert path.exists()


def test_insert_and_latest_reading(db_path):
    assert database.latest_reading(db_path) is None
    database.insert_reading(db_path, telemetry(temp_c=24.0))
    database.insert_reading(db_path, telemetry(temp_c=25.5, lid_open=True))
    latest = database.latest_reading(db_path)
    assert latest["temp_c"] == 25.5
    assert latest["lid_open"] is True
    assert latest["fan_on"] is True
    assert (latest["warning_c"], latest["critical_c"]) == (27.0, 32.0)
    assert latest["received_at"].endswith("+00:00")


def test_readings_since_filters_old_rows(db_path):
    database.insert_reading(db_path, telemetry(temp_c=20.0), received_at="2020-01-01T00:00:00+00:00")
    database.insert_reading(db_path, telemetry(temp_c=24.0))
    readings = database.readings_since(db_path, 60)
    assert [r["temp_c"] for r in readings] == [24.0]


def test_recent_events_newest_first(db_path):
    database.insert_event(db_path, "esp32-rack01", "online")
    database.insert_event(db_path, "esp32-rack01", "state_change", json.dumps({"from": "normal", "to": "warning"}))
    events = database.recent_events(db_path, 10)
    assert [e["kind"] for e in events] == ["state_change", "online"]
    assert database.recent_events(db_path, 1)[0]["kind"] == "state_change"


def test_last_status(db_path):
    assert database.last_status(db_path) is None
    database.insert_event(db_path, "esp32-rack01", "online")
    database.insert_event(db_path, "esp32-rack01", "command", "{}")
    assert database.last_status(db_path) == "online"
    database.insert_event(db_path, "esp32-rack01", "offline")
    assert database.last_status(db_path) == "offline"


def test_text_is_stored_as_parameter(db_path):
    detail = "'); DROP TABLE readings; --"
    database.insert_event(db_path, "esp32-rack01", "command", detail)
    assert database.recent_events(db_path, 1)[0]["detail"] == detail
    assert database.latest_reading(db_path) is None
